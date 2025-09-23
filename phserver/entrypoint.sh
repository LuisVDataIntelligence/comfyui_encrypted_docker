#!/usr/bin/env bash
set -euo pipefail

MODE="${LAUNCH_MODE:-serverless}"

# If no NVIDIA devices or FORCE_CPU=1, hide CUDA devices to prevent PyTorch from trying to init CUDA.
if [[ "${FORCE_CPU:-0}" == "1" || ! -e /dev/nvidiactl || -z "${NVIDIA_VISIBLE_DEVICES:-}" ]]; then
  echo "[entrypoint] No NVIDIA devices detected or FORCE_CPU=1 — forcing CPU mode (hiding CUDA devices)"
  export CUDA_VISIBLE_DEVICES=""
fi

if [[ "$MODE" == "api" ]]; then
  echo "[entrypoint] Starting API server (FastAPI)"
  exec python3 /opt/app/phserver/api_server.py
else
  echo "[entrypoint] Starting RunPod serverless worker"
  exec python3 /opt/app/handler.py
fi
