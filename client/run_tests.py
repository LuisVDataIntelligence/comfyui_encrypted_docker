#!/usr/bin/env python3
import os
import sys
import time
import json
import argparse
from pathlib import Path
import requests

# Allow running from repo root or from client/ folder (for shared import)
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from shared.crypto_secure import encrypt_for_server
except Exception:
    encrypt_for_server = None  # Only needed for encrypted tests


def _headers(api_key: str) -> dict:
    return {
        "authorization": f"Bearer {api_key}",
        "content-type": "application/json",
        "accept": "application/json",
    }


def _status(base: str, api_key: str, job_id: str) -> dict:
    r = requests.get(f"{base}/status/{job_id}", headers=_headers(api_key), timeout=30)
    r.raise_for_status()
    return r.json()


def _poll_until_done(base: str, api_key: str, job_id: str, timeout: int, interval: float = 2.0) -> dict:
    t0 = time.time()
    last = None
    while time.time() - t0 < timeout:
        last = _status(base, api_key, job_id)
        st = (last.get("status") or last.get("state") or "").upper()
        if st in ("COMPLETED", "FAILED", "CANCELLED"):
            return last
        time.sleep(interval)
    return {"status": "TIMEOUT", "last": last}


def _noop_workflow() -> dict:
    # Minimal valid Comfy mapping that the server can accept in DRY_RUN
    return {"noop": {"class_type": "Note", "inputs": {"text": "hello"}}}


def run_plain_runsync(endpoint_id: str, api_key: str, timeout: int = 180) -> dict:
    base = f"https://api.runpod.ai/v2/{endpoint_id}"
    body = {"input": {"workflow": _noop_workflow()}}
    r = requests.post(f"{base}/runsync", headers=_headers(api_key), data=json.dumps(body), timeout=timeout)
    r.raise_for_status()
    out = r.json()
    # Some environments still return IN_QUEUE for runsync; poll if an id is provided.
    st = (out.get("status") or "").upper()
    if st in ("IN_QUEUE", "IN_PROGRESS") and out.get("id"):
        return _poll_until_done(base, api_key, out["id"], timeout)
    return out


def run_plain_async(endpoint_id: str, api_key: str, timeout: int = 180) -> dict:
    base = f"https://api.runpod.ai/v2/{endpoint_id}"
    body = {"input": {"workflow": _noop_workflow()}}
    r = requests.post(f"{base}/run", headers=_headers(api_key), data=json.dumps(body), timeout=30)
    r.raise_for_status()
    enq = r.json()
    jid = enq.get("id")
    if not jid:
        return {"error": "no_job_id", "response": enq}
    return _poll_until_done(base, api_key, jid, timeout)


def run_encrypted_runsync(endpoint_id: str, api_key: str, server_public_key_b64: str, workflow_path: Path | None, timeout: int = 180) -> dict:
    if encrypt_for_server is None:
        return {"error": "pynacl_missing", "hint": "pip install pynacl requests"}
    base = f"https://api.runpod.ai/v2/{endpoint_id}"
    if workflow_path and workflow_path.exists():
        wf = json.loads(workflow_path.read_text())
    else:
        wf = _noop_workflow()
    pt = json.dumps(wf).encode("utf-8")
    payload = encrypt_for_server(server_public_key_b64, pt)
    payload["encrypted"] = True
    # Keep responses small; this does not affect core logic
    payload["return_images"] = False
    r = requests.post(f"{base}/runsync", headers=_headers(api_key), data=json.dumps({"input": payload}), timeout=timeout)
    r.raise_for_status()
    out = r.json()
    st = (out.get("status") or "").upper()
    if st in ("IN_QUEUE", "IN_PROGRESS") and out.get("id"):
        return _poll_until_done(base, api_key, out["id"], timeout)
    return out


def main():
    p = argparse.ArgumentParser(description="RunPod serverless tests for ComfyUI encrypted worker")
    p.add_argument("mode", choices=["quick", "async", "encrypted"], help="Which test to run")
    p.add_argument("--endpoint-id", default=os.getenv("RP_ENDPOINT_ID"), help="RunPod endpoint ID (env RP_ENDPOINT_ID)")
    p.add_argument("--api-key", default=os.getenv("RP_API_KEY"), help="RunPod API key (env RP_API_KEY)")
    p.add_argument("--public-key", default=os.getenv("SERVER_PUBLIC_KEY_B64"), help="Server public key b64 (required for encrypted mode)")
    p.add_argument("--workflow", default=str(Path(__file__).parent / "examples/minimal_text2img.json"), help="Workflow JSON path (encrypted mode); default example")
    p.add_argument("--timeout", type=int, default=180, help="Timeout seconds for runsync/status polling")
    args = p.parse_args()

    if not args.endpoint_id or not args.api_key:
        print("error: endpoint id and api key required (set RP_ENDPOINT_ID and RP_API_KEY)", file=sys.stderr)
        sys.exit(2)

    try:
        if args.mode == "quick":
            res = run_plain_runsync(args.endpoint_id, args.api_key, timeout=args.timeout)
        elif args.mode == "async":
            res = run_plain_async(args.endpoint_id, args.api_key, timeout=args.timeout)
        else:  # encrypted
            if not args.public_key:
                print("error: --public-key or env SERVER_PUBLIC_KEY_B64 required for encrypted mode", file=sys.stderr)
                sys.exit(2)
            res = run_encrypted_runsync(args.endpoint_id, args.api_key, args.public_key, Path(args.workflow), timeout=args.timeout)
        print(json.dumps(res, indent=2))
    except requests.HTTPError as e:
        print(f"http_error: {e}")
        if e.response is not None:
            print(e.response.text)
        sys.exit(1)
    except Exception as e:
        print(f"error: {type(e).__name__}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

