import os, json, sys
from pathlib import Path
import requests

# Allow running from repo root or from the client/ folder
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from shared.crypto_secure import encrypt_for_server

API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8000").rstrip("/")
SERVER_PUBLIC_KEY_B64 = os.getenv("SERVER_PUBLIC_KEY_B64", "")
RUNPOD_API_KEY = os.getenv("RP_API_KEY") or os.getenv("RUNPOD_API_KEY")
WORKFLOW_PATH = os.getenv("WORKFLOW_JSON")  # optional override
RUNPOD_SERVERLESS = os.getenv("RUNPOD_SERVERLESS", "0") in ("1", "true", "TRUE")

if WORKFLOW_PATH:
    workflow_path = Path(WORKFLOW_PATH).expanduser().resolve()
else:
    workflow_path = Path(__file__).resolve().parent / "examples/minimal_text2img.json"

with open(workflow_path, "r") as f:
    workflow = json.load(f)

if SERVER_PUBLIC_KEY_B64:
    payload = encrypt_for_server(SERVER_PUBLIC_KEY_B64, json.dumps(workflow).encode("utf-8"))
    payload["encrypted"] = True
else:
    payload = {"workflow": workflow}

url = f"{API_BASE}/run"
headers = {"Content-Type": "application/json"}
if RUNPOD_API_KEY:
    headers["Authorization"] = f"Bearer {RUNPOD_API_KEY.strip()}"

print(f"POST {url}")
if RUNPOD_API_KEY:
    print("Auth: Bearer <redacted>")
print(f"Encrypted: {bool(payload.get('encrypted'))}")

body = payload
if RUNPOD_SERVERLESS or "/v2/" in API_BASE:
    # Wrap for RunPod serverless endpoint contract { "input": ... }
    body = {"input": payload}
    print("Detected serverless mode -> wrapping payload under 'input'")

resp = requests.post(url, json=body, headers=headers, timeout=120)
print("Status:", resp.status_code)
ct = resp.headers.get("content-type", "")
if "application/json" in ct:
    try:
        print(json.dumps(resp.json(), indent=2)[:5000])
    except Exception:
        print(resp.text[:5000])
else:
    print(resp.text[:5000])
