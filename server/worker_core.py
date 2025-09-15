import os, json, uuid, subprocess, logging
from typing import Any, Dict

from server import comfy_client
from shared.crypto_secure import decrypt_from_client, load_private_key_b64

# --------- Config ---------
MODEL_DIR = os.environ.get("COMFYUI_MODEL_DIR", "/workspace/models")
COMFY_PORT = os.environ.get("COMFY_PORT", "8188")
COMFY_STARTUP_TIMEOUT = int(os.environ.get("COMFY_STARTUP_TIMEOUT", "300"))
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

WORKSPACE = os.environ.get("COMFY_WORKSPACE", "/opt/ComfyUI")

def ensure_dirs():
    os.makedirs(MODEL_DIR, exist_ok=True)
    os.makedirs("/dev/shm/comfy_output", exist_ok=True)
    os.makedirs("/dev/shm/comfy_temp", exist_ok=True)

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
        "--dont-print-server"
    ]
    # If no GPU is visible in the container, force CPU mode so ComfyUI starts.
    force_cpu_env = os.getenv("FORCE_CPU", "0")
    no_gpu_detected = not os.path.exists("/dev/nvidiactl") and not os.getenv("NVIDIA_VISIBLE_DEVICES")
    if force_cpu_env == "1" or no_gpu_detected:
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
    if COMFY_PROC is None or (COMFY_PROC.poll() is not None):
        COMFY_PROC = start_comfy()
        if not comfy_client.wait_for_server(timeout=COMFY_STARTUP_TIMEOUT):
            raise RuntimeError("ComfyUI server failed to start")

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
