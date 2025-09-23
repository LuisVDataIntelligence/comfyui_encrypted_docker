import os, sys, json
from pathlib import Path
import requests

API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8000").rstrip("/")
RUNPOD_API_KEY = os.getenv("RP_API_KEY") or os.getenv("RUNPOD_API_KEY")
SERVER_PUBLIC_KEY_B64 = os.getenv("SERVER_PUBLIC_KEY_B64", "")
RUNPOD_SERVERLESS = os.getenv("RUNPOD_SERVERLESS", "0") in ("1","true","TRUE") or ("/v2/" in API_BASE)

repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))
from shared.crypto_secure import encrypt_for_server

headers = {"Content-Type": "application/json"}
if RUNPOD_API_KEY:
    headers["Authorization"] = f"Bearer {RUNPOD_API_KEY.strip()}"

# 1. /download a very small file (use a tiny text from GitHub raw or similar)
TEST_FILE_URL = os.getenv("TEST_DOWNLOAD_URL", "https://raw.githubusercontent.com/github/gitignore/main/README.md")
req_body = {
    "url": TEST_FILE_URL,
    "type": "checkpoints",
    "filename": "__test_download.txt",
    "overwrite": True
}
print(f"POST {API_BASE}/download -> {TEST_FILE_URL}")
resp = requests.post(f"{API_BASE}/download", json=req_body, headers=headers, timeout=180)
print("Download status:", resp.status_code)
print(resp.text[:800])
if resp.status_code >= 300:
    sys.exit(2)

# 2. List models
print(f"GET {API_BASE}/models/ls")
resp_ls = requests.get(f"{API_BASE}/models/ls", headers=headers, timeout=60)
print("List status:", resp_ls.status_code)
print(resp_ls.text[:1200])

# 3. Optional encrypted /run smoke (small) if public key present
if SERVER_PUBLIC_KEY_B64:
    wf_path = Path(__file__).parent / "examples/minimal_text2img.json"
    with open(wf_path, "r") as f:
        wf = json.load(f)
    payload = encrypt_for_server(SERVER_PUBLIC_KEY_B64, json.dumps(wf).encode())
    payload["encrypted"] = True
    run_body = {"input": payload} if RUNPOD_SERVERLESS else payload
    print(f"POST {API_BASE}/run (encrypted smoke)")
    r2 = requests.post(f"{API_BASE}/run", json=run_body, headers=headers, timeout=180)
    print("Run status:", r2.status_code)
    print(r2.text[:800])
else:
    print("Skipping encrypted /run smoke: SERVER_PUBLIC_KEY_B64 not set")

print("Download test complete.")
