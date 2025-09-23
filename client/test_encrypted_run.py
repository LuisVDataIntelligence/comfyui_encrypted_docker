import os, json, sys, time
from pathlib import Path
import requests

repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from shared.crypto_secure import encrypt_for_server

API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8000").rstrip("/")
SERVER_PUBLIC_KEY_B64 = os.getenv("SERVER_PUBLIC_KEY_B64", "")
RUNPOD_API_KEY = os.getenv("RP_API_KEY") or os.getenv("RUNPOD_API_KEY")
RUNPOD_SERVERLESS = os.getenv("RUNPOD_SERVERLESS", "0") in ("1","true","TRUE") or ("/v2/" in API_BASE)
WORKFLOW_PATH = Path(__file__).parent / "examples/minimal_text2img.json"

with open(WORKFLOW_PATH, "r") as f:
    workflow = json.load(f)

# Always encrypt for this test
if not SERVER_PUBLIC_KEY_B64:
    print("ERROR: SERVER_PUBLIC_KEY_B64 not set")
    sys.exit(1)

payload = encrypt_for_server(SERVER_PUBLIC_KEY_B64, json.dumps(workflow).encode())
payload["encrypted"] = True

headers = {"Content-Type": "application/json"}
if RUNPOD_API_KEY:
    headers["Authorization"] = f"Bearer {RUNPOD_API_KEY.strip()}"

body = {"input": payload} if RUNPOD_SERVERLESS else payload
url = f"{API_BASE}/run"
print(f"POST {url} (encrypted, serverless={RUNPOD_SERVERLESS})")
resp = requests.post(url, json=body, headers=headers, timeout=180)
print("Status:", resp.status_code)
print(resp.text[:4000])

if resp.status_code >= 300:
    sys.exit(2)

print("Encrypted run submission completed.")
