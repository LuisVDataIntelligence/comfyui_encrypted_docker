# handler.py
import os, json, uuid, subprocess, logging
import runpod
from typing import Any, Dict
import comfy_client
from crypto_secure import decrypt_from_client

# --------- Config ---------
MODEL_DIR = os.environ.get("COMFYUI_MODEL_DIR", "/runpod-volume/models")
COMFY_PORT = os.environ.get("COMFY_PORT", "8188")
LOG_LEVEL = os.getenv("LOG_LEVEL", "ERROR").upper()
LOG_SILENT = os.getenv("LOG_SILENT", "1")  # "1" => silence ComfyUI stdout/stderr
NO_HISTORY = os.getenv("NO_HISTORY", "0")  # "1" => don't GET /history
WORKER_PRIVATE_KEY_B64 = os.getenv("WORKER_PRIVATE_KEY_B64", "")

# Logging (quiet by default)
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.ERROR))
for noisy in ("urllib3","requests","websocket","runpod"):
    logging.getLogger(noisy).setLevel(logging.ERROR)
log = logging.getLogger("worker")

WORKSPACE = "/workspace/ComfyUI"

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
        "--headless",
        "--no-sse",
        "--listen", "127.0.0.1",
        "--port", COMFY_PORT,
        "--output-directory", "/dev/shm/comfy_output",
        "--temp-directory", "/dev/shm/comfy_temp",
        "--fast"
    ]
    if LOG_SILENT == "1":
        return subprocess.Popen(cmd, env=env, cwd=WORKSPACE,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        return subprocess.Popen(cmd, env=env, cwd=WORKSPACE)

COMFY_PROC = None

def init():
    global COMFY_PROC
    ensure_dirs()
    if COMFY_PROC is None or (COMFY_PROC.poll() is not None):
        COMFY_PROC = start_comfy()
        if not comfy_client.wait_for_server(timeout=120):
            raise RuntimeError("ComfyUI server failed to start")

init()

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
        except Exception as e:
            log.error("Decrypt failed")
            return {"__error": "invalid ciphertext"}
    else:
        return payload.get("workflow", {})

def handler(event: Dict[str, Any]):
    # The serverless request body should include {"input": {...}}
    data = event.get("input") or {}
    wf = _decrypt_if_needed(data)
    if not isinstance(wf, dict) or "__error" in wf:
        return {"error": wf.get("__error", "Missing or invalid workflow")}

    client_id = data.get("client_id") or f"rp-{uuid.uuid4()}"
    # Execute workflow and return metadata (no prompts echoed)
    res = comfy_client.run_workflow_and_wait(wf, client_id)

    if NO_HISTORY == "1":
        # Return only bare minimum
        return {"status": "ok", "prompt_id": res.get("prompt_id")}

    # Minimal history return; caller decides how to handle artifacts
    return {"status": "ok", "prompt_id": res.get("prompt_id"), "history": res.get("history")}

runpod.serverless.start({"handler": handler})