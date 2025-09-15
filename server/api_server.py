import os
import json
import pathlib
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from server.worker_core import handle_request, init_comfy, MODEL_DIR, server_public_key_b64

DOCS_ENABLED = os.getenv("API_DOCS", "false").lower() == "true"
app = FastAPI(
    title="ComfyUI Secure API",
    version="0.1.0",
    docs_url=("/docs" if DOCS_ENABLED else None),
    redoc_url=("/redoc" if DOCS_ENABLED else None),
    openapi_url=("/openapi.json" if DOCS_ENABLED else None),
)


class RunRequest(BaseModel):
    # Plain or encrypted payload fields (same as serverless 'input')
    workflow: Optional[dict] = None
    encrypted: Optional[bool] = None
    epk: Optional[str] = None
    nonce: Optional[str] = None
    ciphertext: Optional[str] = None
    client_id: Optional[str] = None
    no_history: Optional[bool] = Field(default=None, description="Override history fetch")


MODEL_SUBDIRS = {
    # common ComfyUI model folders
    "checkpoints": "checkpoints",
    "vae": "vae",
    "loras": "loras",
    "lora": "loras",
    "clip": "clip",
    "clip_vision": "clip_vision",
    "controlnet": "controlnet",
    "unet": "unet",
    "upscale": "upscale_models",
    "embeddings": "embeddings",
}


class DownloadRequest(BaseModel):
    url: str
    type: Optional[str] = Field(default=None, description="Model type, e.g. checkpoints, vae, loras, controlnet, etc.")
    dest: Optional[str] = Field(default=None, description="Custom destination path, relative to MODEL_DIR")
    filename: Optional[str] = None
    overwrite: bool = False
    civitai_token: Optional[str] = Field(default=None, description="Civitai API token; sets Authorization: Bearer <token>")
    headers: Optional[dict] = Field(default=None, description="Optional extra HTTP headers to include on the request")


@app.on_event("startup")
def _startup():
    init_comfy()


@app.get("/healthz")
def healthz():
    return {
        "ok": True,
        "model_dir": MODEL_DIR,
        "server_public_key_b64": server_public_key_b64(),
    }


@app.post("/run")
def run_workflow(req: RunRequest):
    data = req.model_dump(exclude_none=True)
    try:
        res = handle_request(data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    if isinstance(res, dict) and res.get("error"):
        raise HTTPException(status_code=400, detail=res["error"])
    return res


def _target_path(req: DownloadRequest) -> pathlib.Path:
    base = pathlib.Path(MODEL_DIR)
    if req.dest:
        target_dir = base / pathlib.Path(req.dest)
    elif req.type:
        sub = MODEL_SUBDIRS.get(req.type.lower())
        if not sub:
            raise HTTPException(status_code=400, detail=f"Unknown model type: {req.type}")
        target_dir = base / sub
    else:
        target_dir = base  # default to root models dir
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir


@app.post("/download")
def download_model(req: DownloadRequest):
    import requests
    from urllib.parse import urlparse

    target_dir = _target_path(req)

    filename = req.filename
    if not filename:
        parsed = urlparse(req.url)
        filename = pathlib.Path(parsed.path).name or "download.bin"

    dest_path = target_dir / filename
    if dest_path.exists() and not req.overwrite:
        return {"status": "exists", "path": str(dest_path)}

    # Build request headers
    hdrs = {}
    if isinstance(req.headers, dict):
        # shallow copy of provided headers
        hdrs.update({str(k): str(v) for k, v in req.headers.items()})
    if req.civitai_token:
        # Add/override Authorization for Civitai; harmless if used elsewhere
        hdrs["Authorization"] = f"Bearer {req.civitai_token}"

    try:
        with requests.get(req.url, stream=True, timeout=120, headers=hdrs, allow_redirects=True) as r:
            r.raise_for_status()
            # If filename not provided, try content-disposition
            if not filename:
                cd = r.headers.get('content-disposition') or r.headers.get('Content-Disposition')
                if cd and 'filename=' in cd:
                    # naive parse; strip quotes if present
                    fname = cd.split('filename=')[-1].strip().strip('"').strip("'")
                    if fname:
                        filename = fname
                        dest_path = target_dir / filename
            with open(dest_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 1024):  # 1MB chunks
                    if chunk:
                        f.write(chunk)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"download_failed: {type(e).__name__}: {str(e)}")

    return {"status": "ok", "path": str(dest_path), "size": dest_path.stat().st_size}


@app.get("/models/ls")
def list_models():
    base = pathlib.Path(MODEL_DIR)
    out = {}
    for name in sorted(MODEL_SUBDIRS.values()):
        p = base / name
        files = []
        if p.exists():
            for child in p.iterdir():
                if child.is_file():
                    files.append({"name": child.name, "size": child.stat().st_size})
        out[name] = files
    return {"dir": MODEL_DIR, "models": out}


if __name__ == "__main__":
    import uvicorn
    # Quiet defaults; no access logs; log level can be overridden via UVICORN_LOG_LEVEL
    log_level = os.getenv("UVICORN_LOG_LEVEL", "warning")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("API_PORT", "8000")),
        access_log=False,
        log_level=log_level,
        proxy_headers=True,
    )
