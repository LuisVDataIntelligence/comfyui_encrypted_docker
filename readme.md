[![Runpod](https://api.runpod.io/badge/LuisVDataIntelligence/comfyui_encrypted_docker)](https://console.runpod.io/hub/LuisVDataIntelligence/comfyui_encrypted_docker)

Awesome—here’s a ready-to-build container plus client scripts (Python + Node) that add:

Application-layer encryption of the workflow (Curve25519 + XSalsa20-Poly1305 via libsodium).

Minimal logging (only ERROR).

No persistent prompt/files (uses RAM for outputs & temp via /dev/shm).

Queue-based RunPod Serverless (no inbound ports) and optional Pod API mode with FastAPI.

You can paste these into a repo as-is and build.

## Project layout

- `server/` — Serverless worker and Pod API server
  - `handler.py` (RunPod serverless entry)
  - `api_server.py` (FastAPI for Pod mode)
  - `worker_core.py` (decrypt + run ComfyUI)
  - `comfy_client.py` (HTTP/WS client for ComfyUI)
  - `requirements.txt` (server deps)
  - `entrypoint.sh` (dispatches serverless vs API)
- `shared/` — Shared crypto helpers
  - `crypto_secure.py` (Curve25519 + XSalsa20-Poly1305)
- `client/` — Submission tools
  - `submit_job.py` (RunPod serverless, Python)
  - `submit_job.mjs` (RunPod serverless, Node)
  - `local_submit.py` (Pod API, local HTTP)
  - `gen_keys.py` (generate server keypair)
  - `examples/minimal_text2img.json`
- `Dockerfile` — builds server image (serverless/pod)

## Crypto helpers

Envelope crypto: Curve25519 (ECDH) + XSalsa20-Poly1305 (NaCl Box).

Server keeps WORKER_PRIVATE_KEY_B64 (base64) secret.

Clients use server’s public key to encrypt per-request.

The server decrypts when `input.encrypted == true`, starts ComfyUI headless with outputs/temp on RAM (/dev/shm), uses minimal logging, and never echoes plaintext workflows in logs or responses.

## Client scripts (encrypt → call RunPod)
1) Python client (encrypts workflow)

### # Generate keys
python client/gen_keys.py

- Put WORKER_PRIVATE_KEY_B64 as an env var on the endpoint (or as a file on /runpod-volume/keys and load it in code).
- Give the public key (SERVER_PUBLIC_KEY_B64) to your client(s).

## Build & Deploy (quick)

Build & push

docker build -t YOUR_DOCKERHUB/comfyui-secure-serverless:latest .
docker push YOUR_DOCKERHUB/comfyui-secure-serverless:latest


Create Serverless endpoint (queue-based) using that image (default).

Attach network volume (models under /runpod-volume/models).

Set env vars:

COMFYUI_MODEL_DIR=/runpod-volume/models
COMFY_PORT=8188
LOG_LEVEL=ERROR
LOG_SILENT=1
NO_HISTORY=0
WORKER_PRIVATE_KEY_B64=<from gen_keys.py>


Put the public key from `client/gen_keys.py` in your client env as `SERVER_PUBLIC_KEY_B64`.

Run the Python or Node client to submit encrypted jobs.

Notes & knobs you can tweak

Even quieter: set NO_HISTORY=1 to skip the /history fetch (least I/O; you’ll only get prompt_id).

Persist results: if you must write images, encrypt them first and save to /runpod-volume (don’t change the RAM output/temp defaults).

Rotate keys: deploy a new WORKER_PRIVATE_KEY_B64, then switch clients to the new public key.

If you want, I can also generate a Load-Balancing + FastAPI variant with Bearer/HMAC and optional Cloudflare Tunnel/Tailscale baked in.

## Pod mode (HTTP API + model downloader)

Set `LAUNCH_MODE=api` and run the container on a Pod. The API listens on `:8000` and keeps ComfyUI bound to localhost.

Endpoints:

- POST `/run`: accepts either `{ workflow: {...} }` or an encrypted envelope `{ encrypted:true, epk, nonce, ciphertext }`. Optional `client_id` and `no_history`.
- POST `/download`: `{ url, type?: 'checkpoints'|'vae'|'loras'|'controlnet'|..., dest?: 'custom/subdir', filename?: 'name.safetensors', overwrite?: false, civitai_token?: '...optional...', headers?: {"Authorization":"Bearer ..."} }` downloads into `$COMFYUI_MODEL_DIR`.
- GET `/models/ls`: lists model files under common subfolders.
- GET `/healthz`: returns `{ ok, model_dir, server_public_key_b64 }`.

Pod env vars (example):

- `LAUNCH_MODE=api`
- `COMFYUI_MODEL_DIR=/workspace/models` (default if unset). If your RunPod volume is mounted at `/workspace`, models will live at `/workspace/models`.
- `WORKER_PRIVATE_KEY_B64=<private key>` (to allow encrypted `/run`)
- `API_PORT=8000` (optional)

Local test:

1) `python client/gen_keys.py` and export `WORKER_PRIVATE_KEY_B64` into container; set `SERVER_PUBLIC_KEY_B64` in your client.
2) Run container with `-p 8000:8000 -e LAUNCH_MODE=api` and mount a volume at `/runpod-volume/models`.
3) `python client/local_submit.py` (uses `SERVER_PUBLIC_KEY_B64` if set) to submit a job.
4) `curl -X POST localhost:8000/download -d '{"url":"https://...","type":"checkpoints"}' -H 'content-type: application/json'` to fetch a model.

Worked for 3 minutes

Here’s a complete package—Docker container plus client scripts—built around the encryption and minimal‑logging recommendations. Download the zip and inspect the contents; you can use it as-is for your RunPod Serverless endpoint.

## What’s inside

Dockerfile: Builds a CUDA‑enabled image, clones ComfyUI and installs dependencies. It installs libsodium via PyNaCl and sets the output/temp directories to /dev/shm to avoid persisting files. The container launches ComfyUI headless and waits for jobs.

server/handler.py: RunPod serverless handler that decrypts incoming workflows when input.encrypted is set, starts ComfyUI silently, and returns only minimal metadata (prompt_id + optional history). It suppresses logs and uses in‑memory storage.

shared/crypto_secure.py: Helpers to generate keypairs and perform envelope encryption/decryption using Curve25519 + XSalsa20‑Poly1305.

server/comfy_client.py: Minimal client for local API calls to ComfyUI (queue prompt, wait via WebSocket).

client/examples/minimal_text2img.json: Simple workflow demonstrating how to specify a model and text prompt.

client/submit_job.py and client/submit_job.mjs: Python and Node scripts that load a workflow, encrypt it with the server’s public key and post it to your endpoint using HTTPS
docs.runpod.io
.

client/gen_keys.py: Generates a server keypair; keep the private key (WORKER_PRIVATE_KEY_B64) secret on your endpoint and share the public key (SERVER_PUBLIC_KEY_B64) with clients.

## Deploy & run

Generate a keypair locally: run python client/gen_keys.py. Save the WORKER_PRIVATE_KEY_B64 value as an environment variable on your RunPod endpoint; share the SERVER_PUBLIC_KEY_B64 with anyone who will submit jobs.

Build & push the image:

docker build -t yourusername/comfyui-secure-serverless:latest .
docker push yourusername/comfyui-secure-serverless:latest


Create a queue‑based serverless endpoint using the image. Attach a network volume for your models (mounts at /runpod-volume). Set these environment variables:

COMFYUI_MODEL_DIR=/runpod-volume/models

WORKER_PRIVATE_KEY_B64=<your private key>

LOG_LEVEL=ERROR, LOG_SILENT=1 for minimal logging

Optionally NO_HISTORY=1 if you don’t want to call /history

Call your endpoint via HTTPS with your RunPod API key docs.runpod.io. Use the provided client scripts to encrypt the workflow: the client builds the JSON payload containing encrypted: true, the nonce, ciphertext and the client’s epk. On the server, server/handler.py decrypts it and forwards the workflow to ComfyUI.

## Notes

The Dockerfile starts ComfyUI with --output-directory and --temp-directory flags; the ComfyUI wiki notes these parameters let you change where outputs are written
comfyui-wiki.com
. Using /dev/shm keeps everything in RAM.

All network requests to RunPod’s API go over HTTPS and require an API key
docs.runpod.io
, providing transport‑layer encryption. The envelope encryption layer ensures the prompt JSON is unreadable even if captured.

Rotate your keys periodically and scope your RunPod API key to this endpoint only for best security.

## Publishing to RunPod Hub (Serverless)

Quick path to a smooth publish:

1) Ensure Dockerfile exists at repo path used by the Hub.
   - This project now includes `WIP_ComfyUI_Docker/Dockerfile` for auto-detection.
   - In the Hub form, set Dockerfile path to `WIP_ComfyUI_Docker/Dockerfile` if needed.

2) Add these environment variables (recommended defaults):
   - `COMFYUI_MODEL_DIR=/workspace/models`
   - `LOG_LEVEL=ERROR` and `LOG_SILENT=1`
   - `NO_HISTORY=0` (or `1` to return only `prompt_id`)
   - `ENCRYPTION_REQUIRED=1` (encrypted-only; set `0` to allow plaintext for testing)
   - `WORKER_PRIVATE_KEY_B64=<REQUIRED: from gen_keys.py>`

3) Define inputs in the Hub form (example below) and save as template.

Example Hub inputs JSON (copy/paste):

```
[
  { "key": "workflow", "input": { "name": "ComfyUI API Workflow", "type": "json", "description": "Comfy /prompt mapping (id->node). Not graph JSON.", "required": false } },
  { "key": "encrypted", "input": { "name": "Encrypted Payload", "type": "boolean", "default": true } },
  { "key": "epk", "input": { "name": "Client Ephemeral Public Key (b64)", "type": "text" } },
  { "key": "nonce", "input": { "name": "Nonce (b64)", "type": "text" } },
  { "key": "ciphertext", "input": { "name": "Ciphertext (b64)", "type": "text" } },
  { "key": "client_id", "input": { "name": "Client ID", "type": "text", "required": false } },
  { "key": "no_history", "input": { "name": "Skip History Fetch", "type": "boolean", "default": false } }
]
```

4) GPU and storage settings:
   - GPU: Any CUDA 12.x (CPU fallback occurs automatically if no GPU)
   - Volume: mount persistent volume to `/workspace/models`

5) Test:
   - Submit a job with the example `client/examples/minimal_text2img.json` as `workflow` (plaintext) only if `ENCRYPTION_REQUIRED=0`.
   - For production, submit encrypted payloads using the provided key tools and client code.


<!-- Removed PromptHelper combined pod instructions per request: this project is strictly an encrypted ComfyUI worker/API. -->
