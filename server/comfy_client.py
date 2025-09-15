# comfy_client.py
import os, time, json
import requests
from websocket import create_connection

COMFY_HOST = os.environ.get("COMFY_HOST", "127.0.0.1")
COMFY_PORT = int(os.environ.get("COMFY_PORT", "8188"))
BASE_HTTP = f"http://{COMFY_HOST}:{COMFY_PORT}"

def wait_for_server(timeout=120):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            r = requests.get(f"{BASE_HTTP}/system_stats", timeout=2)
            if r.status_code == 200:
                return True
        except Exception:
            time.sleep(0.5)
    return False

def queue_prompt(workflow: dict, client_id: str):
    r = requests.post(f"{BASE_HTTP}/prompt", json={"prompt": workflow, "client_id": client_id}, timeout=30)
    r.raise_for_status()
    return r.json()

def get_history(prompt_id: str):
    r = requests.get(f"{BASE_HTTP}/history/{prompt_id}", timeout=30)
    r.raise_for_status()
    return r.json()

def run_workflow_and_wait(workflow: dict, client_id: str):
    res = queue_prompt(workflow, client_id)
    prompt_id = res.get("prompt_id")

    ws_url = f"ws://{COMFY_HOST}:{COMFY_PORT}/ws?clientId={client_id}"
    ws = create_connection(ws_url)
    try:
        while True:
            msg = ws.recv()
            if not msg:
                break
            evt = json.loads(msg)
            if evt.get("type") == "execution_end" and evt.get("data", {}).get("prompt_id") == prompt_id:
                break
    finally:
        ws.close()

    # Minimal fetch (metadata only). You can turn this off if you want even less I/O.
    hist = get_history(prompt_id)
    return {"prompt_id": prompt_id, "history": hist}

