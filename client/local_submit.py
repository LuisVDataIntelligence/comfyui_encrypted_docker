import os, json, sys
from pathlib import Path
import requests

# Allow running from repo root or from the client/ folder
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from shared.crypto_secure import encrypt_for_server

API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8000")
SERVER_PUBLIC_KEY_B64 = os.getenv("SERVER_PUBLIC_KEY_B64", "")

workflow_path = Path(__file__).resolve().parent / "examples/minimal_text2img.json"
with open(workflow_path, "r") as f:
    workflow = json.load(f)

if SERVER_PUBLIC_KEY_B64:
    payload = encrypt_for_server(SERVER_PUBLIC_KEY_B64, json.dumps(workflow).encode("utf-8"))
    payload["encrypted"] = True
else:
    payload = {"workflow": workflow}

resp = requests.post(f"{API_BASE}/run", json=payload, timeout=120)
print(resp.status_code, resp.text)
