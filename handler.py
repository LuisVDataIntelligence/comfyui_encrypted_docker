import os, sys
from typing import Any, Dict

import runpod

# Insert ComfyUI workspace early so its packages (utils/, etc.) resolve before any similarly named top-level modules.
COMFY_PATH = "/opt/ComfyUI"
if COMFY_PATH not in sys.path:
    sys.path.insert(0, COMFY_PATH)

# We only import worker_core lazily inside handler so that in DRY_RUN mode (and simple health/shape tests)
# we don't pay the cost of spawning ComfyUI or trip over import ordering issues. This also lets the
# RunPod harness start instantly for encrypted smoke tests.

DRY_RUN = os.getenv("DRY_RUN", "0").lower() in ("1", "true", "yes")

def _lazy_import():
    from phserver.worker_core import handle_request, init_comfy  # type: ignore
    return handle_request, init_comfy

_COMFY_INIT_DONE = False

def handler(event: Dict[str, Any]):
    global _COMFY_INIT_DONE
    data = event.get("input") or {}

    # Fast path: DRY_RUN short-circuit without touching ComfyUI.
    if DRY_RUN:
        # Still enforce encryption flag if ENCRYPTION_REQUIRED=1 (logic handled downstream if needed),
        # but we don't import heavy modules—just mimic worker response.
        # If caller sends an encrypted envelope we just acknowledge.
        # Consistent shape with real response.
        return {"status": "ok", "prompt_id": "dry-run"}

    handle_request, init_comfy = _lazy_import()
    if not _COMFY_INIT_DONE:
        # Initialize ComfyUI only once.
        try:
            init_comfy()
        except Exception as e:
            # Surface structured error instead of crash so the RunPod harness can return JSON.
            return {"error": f"comfy_init_failed: {type(e).__name__}: {str(e)}"}
        _COMFY_INIT_DONE = True

    return handle_request(data)


runpod.serverless.start({"handler": handler})
