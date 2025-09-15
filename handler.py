import os
import runpod
from typing import Any, Dict

from phserver.worker_core import handle_request, init_comfy

# Initialize ComfyUI unless in DRY_RUN (used by Hub tests)
if os.getenv("DRY_RUN", "0").lower() not in ("1", "true", "yes"):
    init_comfy()


def handler(event: Dict[str, Any]):
    data = event.get("input") or {}
    return handle_request(data)


runpod.serverless.start({"handler": handler})
