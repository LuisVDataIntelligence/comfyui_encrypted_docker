import os, json, requests
from shared.crypto_secure import encrypt_for_server

API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8000")
SERVER_PUBLIC_KEY_B64 = os.getenv("SERVER_PUBLIC_KEY_B64", "")

with open("client/examples/minimal_text2img.json", "r") as f:
    workflow = json.load(f)

if SERVER_PUBLIC_KEY_B64:
    payload = encrypt_for_server(SERVER_PUBLIC_KEY_B64, json.dumps(workflow).encode("utf-8"))
    payload["encrypted"] = True
else:
    payload = {"workflow": workflow}

resp = requests.post(f"{API_BASE}/run", json=payload, timeout=120)
print(resp.status_code, resp.text)
