Awesome—here’s a ready-to-build container plus client scripts (Python + Node) that add:

Application-layer encryption of the workflow (Curve25519 + XSalsa20-Poly1305 via libsodium).

Minimal logging (only ERROR).

No persistent prompt/files (uses RAM for outputs & temp via /dev/shm).

Queue-based RunPod Serverless (no inbound ports).

You can paste these into a repo as-is and build.

## crypto_secure.py

Envelope crypto: Curve25519 (ECDH) + XSalsa20-Poly1305 (NaCl Box).

Server keeps WORKER_PRIVATE_KEY_B64 (base64) secret.

Clients use server’s public key to encrypt per-request.

## comfy_client.py

Local helper to talk to headless ComfyUI (127.0.0.1:8188)

## handler.py

Decrypts when input.encrypted == true.

Starts headless ComfyUI with outputs/temp on RAM (/dev/shm).

Minimal logging (default ERROR).

Never echoes the plaintext workflow in logs or responses.

## Client scripts (encrypt → call RunPod)
1) Python client (encrypts workflow)

### # gen_keys.py
from crypto_secure import gen_keypair_b64
pk, sk = gen_keypair_b64()
print("SERVER_PUBLIC_KEY_B64=", pk)
print("WORKER_PRIVATE_KEY_B64=", sk)

- Put WORKER_PRIVATE_KEY_B64 as an env var on the endpoint (or as a file on /runpod-volume/keys and load it in code).
- Give the public key (SERVER_PUBLIC_KEY_B64) to your client(s).

## Build & Deploy (quick)

Build & push

docker build -t YOUR_DOCKERHUB/comfyui-secure-serverless:latest .
docker push YOUR_DOCKERHUB/comfyui-secure-serverless:latest


Create Serverless endpoint (queue-based) using that image.

Attach network volume (models under /runpod-volume/models).

Set env vars:

COMFYUI_MODEL_DIR=/runpod-volume/models
COMFY_PORT=8188
LOG_LEVEL=ERROR
LOG_SILENT=1
NO_HISTORY=0
WORKER_PRIVATE_KEY_B64=<from gen_keys.py>


Put the public key from gen_keys.py in your client env as SERVER_PUBLIC_KEY_B64.

Run the Python or Node client to submit encrypted jobs.

Notes & knobs you can tweak

Even quieter: set NO_HISTORY=1 to skip the /history fetch (least I/O; you’ll only get prompt_id).

Persist results: if you must write images, encrypt them first and save to /runpod-volume (don’t change the RAM output/temp defaults).

Rotate keys: deploy a new WORKER_PRIVATE_KEY_B64, then switch clients to the new public key.

If you want, I can also generate a Load-Balancing + FastAPI variant with Bearer/HMAC and optional Cloudflare Tunnel/Tailscale baked in.

Worked for 3 minutes

Here’s a complete package—Docker container plus client scripts—built around the encryption and minimal‑logging recommendations. Download the zip and inspect the contents; you can use it as-is for your RunPod Serverless endpoint.

## What’s inside

Dockerfile: Builds a CUDA‑enabled image, clones ComfyUI and installs dependencies. It installs libsodium via PyNaCl and sets the output/temp directories to /dev/shm to avoid persisting files. The container launches ComfyUI headless and waits for jobs.

handler.py: RunPod serverless handler that decrypts incoming workflows when input.encrypted is set, starts ComfyUI silently, and returns only minimal metadata (prompt_id + optional history). It suppresses logs and uses in‑memory storage.

crypto_secure.py: Helpers to generate keypairs and perform envelope encryption/decryption using Curve25519 + XSalsa20‑Poly1305.

comfy_client.py: Minimal client for local API calls to ComfyUI (queue prompt, wait via WebSocket).

examples/minimal_text2img.json: Simple workflow demonstrating how to specify a model and text prompt.

client_encrypt_send.py and client_encrypt_send.mjs: Python and Node scripts that load a workflow, encrypt it with the server’s public key and post it to your endpoint using HTTPS
docs.runpod.io
.

gen_keys.py: Generates a server keypair; keep the private key (WORKER_PRIVATE_KEY_B64) secret on your endpoint and share the public key (SERVER_PUBLIC_KEY_B64) with clients.

## Deploy & run

Generate a keypair locally: run python gen_keys.py. Save the WORKER_PRIVATE_KEY_B64 value as an environment variable on your RunPod endpoint; share the SERVER_PUBLIC_KEY_B64 with anyone who will submit jobs.

Build & push the image:

docker build -t yourusername/comfyui-secure-serverless:latest .
docker push yourusername/comfyui-secure-serverless:latest


Create a queue‑based serverless endpoint using the image. Attach a network volume for your models (mounts at /runpod-volume). Set these environment variables:

COMFYUI_MODEL_DIR=/runpod-volume/models

WORKER_PRIVATE_KEY_B64=<your private key>

LOG_LEVEL=ERROR, LOG_SILENT=1 for minimal logging

Optionally NO_HISTORY=1 if you don’t want to call /history

Call your endpoint via HTTPS with your RunPod API key
docs.runpod.io
. Use the provided client scripts to encrypt the workflow: the client builds the JSON payload containing encrypted: true, the nonce, ciphertext and the client’s epk. On the server, handler.py decrypts it and forwards the workflow to ComfyUI.

## Notes

The Dockerfile starts ComfyUI with --output-directory and --temp-directory flags; the ComfyUI wiki notes these parameters let you change where outputs are written
comfyui-wiki.com
. Using /dev/shm keeps everything in RAM.

All network requests to RunPod’s API go over HTTPS and require an API key
docs.runpod.io
, providing transport‑layer encryption. The envelope encryption layer ensures the prompt JSON is unreadable even if captured.

Rotate your keys periodically and scope your RunPod API key to this endpoint only for best security.