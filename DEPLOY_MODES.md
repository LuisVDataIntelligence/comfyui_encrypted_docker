# Deployment Modes: Pod API vs Serverless

This image can run in two distinct modes controlled by `LAUNCH_MODE`:

| Mode | Env Value | Purpose | Network | Entry Behavior |
|------|-----------|---------|---------|----------------|
| Pod API | `api` | Long‑lived HTTP API with `/run`, `/download`, `/models/ls`, `/healthz` | Expose `API_PORT` (default 8000, settable to 80) | FastAPI + ComfyUI started as a subprocess |
| Serverless | `serverless` (default) | RunPod queue based (runsync/run) minimal worker | No inbound port required (RunPod proxy uses `/v2/<ENDPOINT>/...`) | RunPod harness -> `handler.py` (lazy ComfyUI init) |

## Core Environment Variables

| Variable | Description | Typical Pod | Typical Serverless |
|----------|-------------|-------------|--------------------|
| `LAUNCH_MODE` | `api` or `serverless` | `api` | `serverless` |
| `API_PORT` | Port FastAPI binds to (api mode only) | `80` or `8000` | (ignored) |
| `COMFYUI_MODEL_DIR` | Model storage root | `/workspace/models` (persist volume) | `/workspace/models` (ephemeral unless volume attached) |
| `WORKER_PRIVATE_KEY_B64` | Curve25519 private key (enables encrypted `/run`) | required (if encryption) | required (if encryption) |
| `ENCRYPTION_REQUIRED` | `1` enforce only encrypted payloads | `1` | `1` |
| `DRY_RUN` | `1` short-circuit success without launching ComfyUI | `0` | `1` for fast smoke tests |
| `NO_HISTORY` | `1` return only `prompt_id` | optional | optional |
| `LOG_SILENT` | `1` suppress logs | `1` (after validation) | `1` |

## Pod Mode Endpoints

Base URL: `http://<pod-host>:<API_PORT>` (or RunPod proxy). Endpoints:

* `GET /healthz` – `{ ok, model_dir, server_public_key_b64 }`
* `POST /run` – Plain `{ "workflow": { ... } }` or encrypted envelope `{ encrypted, epk, nonce, ciphertext }`
* `POST /download` – Download models into `COMFYUI_MODEL_DIR` (types map to subfolders)
* `GET /models/ls` – Lists models

## Serverless Mode Invocation

RunPod paths (example endpoint ID `LOCAL`):

* `POST /v2/LOCAL/runsync` – Waits for completion (DRY_RUN returns immediately)
* `POST /v2/LOCAL/run` – Async; poll `/v2/LOCAL/status/<id>`

Body shape expected by the platform: `{ "input": { ...payload... } }` where payload is either:

Plain (if `ENCRYPTION_REQUIRED=0`):
```json
{ "input": { "workflow": { "1": { "class_type": "EmptyLatentImage", "inputs": {"batch_size":1} } } } }
```

Encrypted:
```json
{ "input": { "encrypted": true, "epk": "<b64>", "nonce": "<b64>", "ciphertext": "<b64>" } }
```

`handler.py` now lazily initializes ComfyUI only when *not* `DRY_RUN` to eliminate startup crashes during quick tests and to allow encryption smoke tests even if models/GPU are absent.

## Download Support in Serverless

The `/download` endpoint is only available in Pod API mode. For serverless you must bake required models into the image or switch to a Pod for bulk downloads, then shift back to serverless once cached in the image or on a shared volume.

## Quick Recipes

### Start Pod on Port 80
Set env:
```
LAUNCH_MODE=api
API_PORT=80
COMFYUI_MODEL_DIR=/workspace/models
WORKER_PRIVATE_KEY_B64=<private>
ENCRYPTION_REQUIRED=1
LOG_SILENT=1
```
Then health: `curl http://<proxy>/healthz`

### Serverless Dry-Run Encryption Smoke
```
ENCRYPTION_REQUIRED=1
DRY_RUN=1
WORKER_PRIVATE_KEY_B64=<private>
```
Client env:
```
RP_ENDPOINT_ID=<id>
RP_API_KEY=<key>
SERVER_PUBLIC_KEY_B64=<pub>
RUNPOD_SERVERLESS=1
```
Run: `python client/test_encrypted_run.py`

### Real Execution (Serverless)
Unset `DRY_RUN` or set `DRY_RUN=0`. Ensure models are available (baked into image) otherwise the workflow referencing them will fail inside ComfyUI.

## Error Reference
| Error | Meaning | Fix |
|-------|---------|-----|
| `comfy_init_failed:*` | ComfyUI failed during startup | Check GPU/CPU mode, logs, model directory permissions |
| `encryption_required` | Plaintext sent while `ENCRYPTION_REQUIRED=1` | Send encrypted envelope or relax flag |
| `missing encrypted fields` | Envelope lacked epk/nonce/ciphertext | Ensure client crypto wrapper correct |
