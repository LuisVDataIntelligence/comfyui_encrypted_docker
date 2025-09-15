import os, json, base64, requests, sys
from pathlib import Path

# Allow running from repo root or from the client/ folder
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from shared.crypto_secure import encrypt_for_server

# --- configure ---
ENDPOINT_ID = os.getenv("RP_ENDPOINT_ID")  # e.g. "abc123def"
API_KEY = os.getenv("RP_API_KEY")          # RunPod API key
SERVER_PUBLIC_KEY_B64 = os.getenv("SERVER_PUBLIC_KEY_B64")  # base64 public key
RUNSYNC = True  # True => /runsync; False => /run + poll later

workflow_path = Path(__file__).resolve().parent / "examples/minimal_text2img.json"
with open(workflow_path, "r") as f:
    workflow = json.load(f)

# Envelope encrypt
payload = encrypt_for_server(SERVER_PUBLIC_KEY_B64, json.dumps(workflow).encode("utf-8"))
payload["encrypted"] = True
payload["return_images"] = False  # keep responses light

url = f"https://api.runpod.ai/v2/{ENDPOINT_ID}/" + ("runsync" if RUNSYNC else "run")
headers = {
    "authorization": API_KEY,
    "content-type": "application/json",
    "accept": "application/json",
}
body = { "input": payload }

r = requests.post(url, headers=headers, data=json.dumps(body), timeout=120)
r.raise_for_status()
print(r.json())
