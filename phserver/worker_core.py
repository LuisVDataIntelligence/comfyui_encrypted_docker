import os, json, uuid, subprocess, logging
from shared.env_loader import load_dotenv_if_present
from typing import Any, Dict

from phserver import comfy_client
from shared.crypto_secure import decrypt_from_client, load_private_key_b64

# --------- Config ---------
# Load .env (best-effort) without overriding already-set environment
load_dotenv_if_present()
MODEL_DIR = os.environ.get("COMFYUI_MODEL_DIR", "/workspace/models")
COMFY_PORT = os.environ.get("COMFY_PORT", "8188")
COMFY_STARTUP_TIMEOUT = int(os.environ.get("COMFY_STARTUP_TIMEOUT", "300"))
# DEVICE_MODE: cpu|gpu|auto  (auto = use GPU if visible, else CPU). Allows explicit CPU pod without relying on GPU detection quirks.
DEVICE_MODE = os.environ.get("DEVICE_MODE", "auto").lower()
# COMFY_AUTOSTART=0 means: do not spawn ComfyUI on module import / init; wait until first workflow request.
COMFY_AUTOSTART = os.environ.get("COMFY_AUTOSTART", "1").lower() in ("1","true","yes")
LOG_LEVEL = os.getenv("LOG_LEVEL", "ERROR").upper()
LOG_SILENT = os.getenv("LOG_SILENT", "1")  # "1" => silence ComfyUI stdout/stderr
NO_HISTORY = os.getenv("NO_HISTORY", "0")  # "1" => don't GET /history
# Require encrypted payloads by default for security. Set to "0" to allow plaintext workflows for testing.
ENCRYPTION_REQUIRED = os.getenv("ENCRYPTION_REQUIRED", "1").lower() in ("1", "true", "yes")
DRY_RUN = os.getenv("DRY_RUN", "0").lower() in ("1", "true", "yes")
WORKER_PRIVATE_KEY_B64 = os.getenv("WORKER_PRIVATE_KEY_B64", "")

# Logging (quiet by default)
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.ERROR))
for noisy in ("urllib3","requests","websocket","runpod"):
    logging.getLogger(noisy).setLevel(logging.ERROR)
log = logging.getLogger("worker")

# If LOG_SILENT is enabled, suppress all Python logging (useful after validation)
# This will silence the Python logging subsystem (handlers) while preserving
# the option to capture raw stdout/stderr if needed. Use this flag cautiously
# during debugging; set LOG_SILENT=0 to enable logs again.
try:
    if str(LOG_SILENT).strip().lower() in ("1", "true", "yes"):
        # Disable all logging at CRITICAL level (effectively silences logging)
        logging.disable(logging.CRITICAL)
except Exception:
    pass

WORKSPACE = os.environ.get("COMFY_WORKSPACE", "/opt/ComfyUI")

def ensure_dirs():
    os.makedirs(MODEL_DIR, exist_ok=True)
    os.makedirs("/dev/shm/comfy_output", exist_ok=True)
    os.makedirs("/dev/shm/comfy_temp", exist_ok=True)
    os.makedirs("/dev/shm/comfy_input", exist_ok=True)

def start_comfy():
    """
    Launch ComfyUI in headless mode, bound to localhost, with RAM-only output/temp.
    """
    env = os.environ.copy()
    env["COMFYUI_MODEL_DIR"] = MODEL_DIR

    cmd = [
        "python3", f"{WORKSPACE}/main.py",
        "--disable-auto-launch",
        "--listen", "127.0.0.1",
        "--port", COMFY_PORT,
        "--output-directory", "/dev/shm/comfy_output",
        "--temp-directory", "/dev/shm/comfy_temp",
        "--input-directory", "/dev/shm/comfy_input",
        "--dont-print-server"
    ]
    # If no GPU is visible in the container, force CPU mode so ComfyUI starts.
    force_cpu_env = os.getenv("FORCE_CPU", "0")
    no_gpu_detected = not os.path.exists("/dev/nvidiactl") and not os.getenv("NVIDIA_VISIBLE_DEVICES")
    device_force_cpu = (
        DEVICE_MODE == "cpu" or
        (DEVICE_MODE == "auto" and (force_cpu_env == "1" or no_gpu_detected))
    )
    if device_force_cpu:
        # Prevent PyTorch from attempting CUDA init by hiding CUDA devices when in CPU-only mode.
        # This avoids RuntimeError: Found no NVIDIA driver on your system during import.
        env["CUDA_VISIBLE_DEVICES"] = ""
        cmd.append("--cpu")
    if LOG_SILENT == "1":
        return subprocess.Popen(cmd, env=env, cwd=WORKSPACE,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        return subprocess.Popen(cmd, env=env, cwd=WORKSPACE)

COMFY_PROC = None

def init_comfy():
    global COMFY_PROC
    ensure_dirs()
    # Warn if encryption is required but no private key is present
    if ENCRYPTION_REQUIRED and not WORKER_PRIVATE_KEY_B64:
        log.warning("WORKER_PRIVATE_KEY_B64 is missing while ENCRYPTION_REQUIRED=1; encrypted requests will fail")
    if COMFY_PROC is None or (COMFY_PROC.poll() is not None):
        try:
            COMFY_PROC = start_comfy()
            if not comfy_client.wait_for_server(timeout=COMFY_STARTUP_TIMEOUT):
                # Check process status
                if COMFY_PROC.poll() is not None:
                    log.error(f"ComfyUI process exited with code: {COMFY_PROC.returncode}")
                raise RuntimeError(f"ComfyUI server failed to start within {COMFY_STARTUP_TIMEOUT}s")
        except Exception as e:
            log.error(f"ComfyUI initialization failed: {e}")
            # Try to get more details if process exists
            if COMFY_PROC and COMFY_PROC.poll() is not None:
                log.error(f"ComfyUI exit code: {COMFY_PROC.returncode}")
            raise

def server_public_key_b64() -> str:
    """Derive and return the server public key (base64) if private key is set."""
    if not WORKER_PRIVATE_KEY_B64:
        return ""
    try:
        sk = load_private_key_b64(WORKER_PRIVATE_KEY_B64)
        return __import__("base64").b64encode(bytes(sk.public_key)).decode()
    except Exception:
        return ""

def _decrypt_if_needed(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    If payload contains encrypted content, decrypt and return a workflow dict.
    Expected fields in payload:
      encrypted: true
      epk, nonce, ciphertext: base64 strings
    Otherwise return payload['workflow'] as-is.
    """
    if payload.get("encrypted"):
        if not WORKER_PRIVATE_KEY_B64:
            raise RuntimeError("Worker private key not set (WORKER_PRIVATE_KEY_B64)")

        epk = payload.get("epk", "")
        nonce = payload.get("nonce", "")
        ciphertext = payload.get("ciphertext", "")
        if not (epk and nonce and ciphertext):
            return {"__error": "missing encrypted fields"}

        try:
            pt = decrypt_from_client(WORKER_PRIVATE_KEY_B64, epk, nonce, ciphertext)
            return json.loads(pt.decode("utf-8"))
        except Exception:
            log.error("Decrypt failed")
            return {"__error": "invalid ciphertext"}
    else:
        return payload.get("workflow", {})

def _handle_input_images(data: Dict[str, Any]) -> None:
    """
    Handle input_images in the payload by saving them to /dev/shm/comfy_input/
    Expected format:
    {
      "input_images": {
        "filename.png": "data:image/png;base64,iVBORw0KGgo...",
        "another.jpg": "https://example.com/image.jpg"
      }
    }
    """
    input_images = data.get("input_images", {})
    if not input_images:
        return

    import base64
    import requests
    from urllib.parse import urlparse

    for filename, image_data in input_images.items():
        try:
            if isinstance(image_data, str):
                if image_data.startswith("data:"):
                    # Base64 encoded image
                    header, encoded = image_data.split(',', 1)
                    decoded = base64.b64decode(encoded)
                    with open(f"/dev/shm/comfy_input/{filename}", "wb") as f:
                        f.write(decoded)
                    log.info(f"Saved base64 image: {filename}")
                elif image_data.startswith("http"):
                    # URL reference - download it
                    response = requests.get(image_data, timeout=30)
                    response.raise_for_status()
                    with open(f"/dev/shm/comfy_input/{filename}", "wb") as f:
                        f.write(response.content)
                    log.info(f"Downloaded image: {filename}")
        except Exception as e:
            log.error(f"Failed to process image {filename}: {e}")

def handle_request(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Accepts a dict with either an encrypted payload or a plain 'workflow' mapping.
    Starts ComfyUI if needed, queues the workflow, waits, and returns minimal metadata.
    """
    init_comfy()

    # DRY-RUN short circuit for Hub tests / smoke checks
    if DRY_RUN:
        return {"status": "ok", "prompt_id": "dry-run"}

    # Enforce encrypted-only mode unless explicitly disabled (still applies when not DRY_RUN)
    if ENCRYPTION_REQUIRED and not data.get("encrypted"):
        return {"error": "encryption_required: set ENCRYPTION_REQUIRED=0 to allow plaintext for testing"}

    wf = _decrypt_if_needed(data)
    # Basic validation and friendly guidance if the wrong JSON shape was sent
    if not isinstance(wf, dict):
        return {"error": "Missing or invalid workflow: expected an API prompt mapping (id->node)"}
    if "__error" in wf:
        return {"error": wf.get("__error", "Invalid encrypted payload")}

    # Handle input images before workflow execution
    try:
        _handle_input_images(data)
    except Exception as e:
        log.error(f"Image handling failed: {e}")
        return {"error": f"image_processing_failed: {e}"}
    # Detect ComfyUI graph-editor export (nodes/links) and guide the user
    if any(k in wf for k in ("nodes", "links", "last_node_id")):
        return {
            "error": "Invalid workflow format: received a graph export (nodes/links). Send an API-ready prompt mapping instead.",
            "hint": "Use a client that converts ComfyUI graph JSON to the /prompt API format (id->node mapping with class_type/inputs)."
        }

    client_id = data.get("client_id") or f"rp-{uuid.uuid4()}"
    # Allow per-request override of history behavior
    no_history_req = str(data.get("no_history", "")).strip()
    no_history = (NO_HISTORY == "1") or (no_history_req == "1" or no_history_req.lower() == "true")

    try:
        res = comfy_client.run_workflow_and_wait(wf, client_id)
    except Exception as e:
        log.exception("workflow execution failed")
        return {"error": f"execution_failed: {type(e).__name__}: {str(e)}"}

    if no_history:
        # Return only bare minimum
        return {"status": "ok", "prompt_id": res.get("prompt_id")}

    # Minimal history return; caller decides how to handle artifacts
    return {"status": "ok", "prompt_id": res.get("prompt_id"), "history": res.get("history")}
