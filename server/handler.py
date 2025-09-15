import runpod
from typing import Any, Dict

# Server imports
from server.worker_core import handle_request, init_comfy

# Ensure ComfyUI is up for the Serverless worker.
init_comfy()


def handler(event: Dict[str, Any]):
    # The serverless request body should include {"input": {...}}
    data = event.get("input") or {}
    return handle_request(data)


runpod.serverless.start({"handler": handler})
