import os
from shared.env_loader import load_dotenv_if_present
import runpod
from typing import Any, Dict

# Load .env (best-effort) before reading environment
load_dotenv_if_present()

# Server imports
from server.worker_core import handle_request, init_comfy

# Ensure ComfyUI is up for the Serverless worker unless DRY_RUN enabled.
if os.getenv("DRY_RUN", "0").lower() not in ("1", "true", "yes"):  # skip in tests
    init_comfy()


def handler(event: Dict[str, Any]):
    # The serverless request body should include {"input": {...}}
    data = event.get("input") or {}
    return handle_request(data)


runpod.serverless.start({"handler": handler})
