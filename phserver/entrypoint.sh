#!/usr/bin/env bash
set -euo pipefail

MODE="${LAUNCH_MODE:-serverless}"

if [[ "$MODE" == "api" ]];
then
  echo "[entrypoint] Starting API server (FastAPI)"
exec python3 /opt/app/phserver/api_server.py
else
  echo "[entrypoint] Starting RunPod serverless worker"
exec python3 /opt/app/handler.py
fi
