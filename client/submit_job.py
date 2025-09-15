# client_encrypt_send.py
import os, json, base64, requests
from shared.crypto_secure import encrypt_for_server

# --- configure ---
ENDPOINT_ID = os.getenv("RP_ENDPOINT_ID")  # e.g. "abc123def"
API_KEY = os.getenv("RP_API_KEY")          # RunPod API key
SERVER_PUBLIC_KEY_B64 = os.getenv("SERVER_PUBLIC_KEY_B64")  # base64 public key
RUNSYNC = True  # True => /runsync; False => /run + poll later

with open("client/examples/minimal_text2img.json", "r") as f:
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
