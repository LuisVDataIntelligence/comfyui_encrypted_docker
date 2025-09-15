# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose
This is a secure, encrypted ComfyUI Docker container for RunPod Serverless deployment. It provides application-layer encryption for workflows, minimal logging, RAM-only storage, and queue-based processing without exposed ports.

## Architecture Overview

### Core Components
- **server/handler.py**: RunPod serverless handler that decrypts workflows and manages ComfyUI execution
- **shared/crypto_secure.py**: Curve25519 + XSalsa20-Poly1305 encryption utilities using PyNaCl
- **server/comfy_client.py**: Local ComfyUI API client for workflow execution and WebSocket monitoring
- **client/submit_job.py**: Client script for encrypting and sending workflows to RunPod endpoints

### Security Architecture
- **Encryption**: End-to-end encryption using Curve25519 ECDH + XSalsa20-Poly1305 NaCl Box
- **Key Management**: Server holds `WORKER_PRIVATE_KEY_B64`, clients use corresponding public key
- **Ephemeral Keys**: Each request uses ephemeral client keypairs for forward secrecy
- **RAM-only Storage**: ComfyUI outputs and temp files stored in `/dev/shm` (no persistence)

### Container Architecture
- **Base**: NVIDIA CUDA 12.4.1 with PyTorch CUDA 12.1 wheels
- **ComfyUI**: Headless mode on localhost:8188 with RAM-only directories
- **Models**: Mounted from RunPod network volume at `/runpod-volume/models`
- **Logging**: Minimal (ERROR level) with optional stdout/stderr suppression

## Development Commands

### Docker Operations
```bash
# Build and push container
docker build -t USERNAME/comfyui-secure-serverless:latest .
docker push USERNAME/comfyui-secure-serverless:latest
```

### Key Generation
```bash
# Generate server keypair (run locally)
python3 -c "from shared.crypto_secure import gen_keypair_b64; pk, sk = gen_keypair_b64(); print(f'SERVER_PUBLIC_KEY_B64={pk}'); print(f'WORKER_PRIVATE_KEY_B64={sk}')"
```

### Testing Locally
```bash
# Install dependencies
pip install -r server/requirements.txt

# Test encryption/decryption
python3 -c "from shared.crypto_secure import *; pk, sk = gen_keypair_b64(); print('Keys generated successfully')"

# Test client workflow encryption
python3 client/submit_job.py  # Requires environment variables
```

## Environment Variables

### Required for Deployment
- `WORKER_PRIVATE_KEY_B64`: Server's private key (keep secret)
- `COMFYUI_MODEL_DIR`: Path to models (default: `/runpod-volume/models`)

### Optional Configuration
- `COMFY_PORT`: ComfyUI port (default: `8188`)
- `LOG_LEVEL`: Logging level (default: `ERROR`)
- `LOG_SILENT`: Suppress ComfyUI stdout/stderr (`1` = silent, default: `1`)
- `NO_HISTORY`: Skip history fetch (`1` = skip, default: `0`)

### Client Environment
- `RP_ENDPOINT_ID`: RunPod endpoint ID
- `RP_API_KEY`: RunPod API key
- `SERVER_PUBLIC_KEY_B64`: Server's public key for encryption

## RunPod Deployment

### Endpoint Configuration
1. Create queue-based serverless endpoint
2. Use built Docker image
3. Attach network volume for models
4. Set environment variables (see above)
5. Configure auto-scaling and timeout settings

### Client Usage
Clients send encrypted payloads with structure:
```json
{
  "input": {
    "encrypted": true,
    "epk": "base64_ephemeral_public_key",
    "nonce": "base64_nonce",
    "ciphertext": "base64_encrypted_workflow"
  }
}
```

## Code Conventions
- **Error Handling**: Minimal logging, no plaintext workflow exposure in logs
- **Security**: Never log decrypted content or private keys
- **Performance**: Use RAM storage, minimal I/O, optional history skipping
- **Dependencies**: Pin versions for reproducible builds (see requirements.txt)

## File Structure
- `/workspace/ComfyUI/`: ComfyUI installation
- `/dev/shm/comfy_output/`: RAM-based output directory
- `/dev/shm/comfy_temp/`: RAM-based temp directory
- `/runpod-volume/models/`: Network volume for model storage
- `examples/`: Sample workflows in ComfyUI API format
