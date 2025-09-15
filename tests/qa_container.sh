#!/usr/bin/env bash
set -euo pipefail

# Simple QA: build and run container locally (CPU), verify /healthz responds.

IMG=${IMG:-comfyui-encrypted:qa}
CONTEXT_DIR=${CONTEXT_DIR:-.}
PORT=${PORT:-8000}

echo "[qa] Building image: $IMG"
docker build -t "$IMG" -f "$CONTEXT_DIR/Dockerfile" "$CONTEXT_DIR"

echo "[qa] Starting container (DRY_RUN=1, LAUNCH_MODE=api)"
CID=$(docker run -d -p ${PORT}:8000 \
  -e LAUNCH_MODE=api \
  -e DRY_RUN=1 \
  -e ENCRYPTION_REQUIRED=0 \
  "$IMG")

cleanup() { docker rm -f "$CID" >/dev/null 2>&1 || true; }
trap cleanup EXIT

echo "[qa] Waiting for /healthz"
for i in {1..60}; do
  if curl -fsS "http://127.0.0.1:${PORT}/healthz" >/dev/null; then
    echo "[qa] OK: /healthz responded"
    exit 0
  fi
  sleep 2
done

echo "[qa] ERROR: /healthz did not respond in time"
docker logs "$CID" || true
exit 1

