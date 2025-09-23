#!/usr/bin/env python3
"""
Download models from CivitAI using Pod API with token from .env file.
"""

import os
import json
import requests
import sys
from pathlib import Path

# Add repo root to path for shared modules
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from shared.env_loader import load_dotenv_if_present

def download_from_civitai(pod_url, model_url, model_type, filename=None, overwrite=False):
    """
    Download a model from CivitAI using Pod API.

    Args:
        pod_url: Pod API base URL (e.g. https://abc123-8000.proxy.runpod.net)
        model_url: CivitAI model download URL
        model_type: Model category (checkpoints, loras, vae, etc.)
        filename: Optional custom filename
        overwrite: Whether to overwrite existing files
    """

    # Load environment variables (including .env files)
    load_dotenv_if_present()

    # Get CivitAI token from environment
    civitai_token = os.getenv("CIVITAI_TOKEN") or os.getenv("CIVITAI_API_TOKEN")
    if not civitai_token:
        print("⚠️  No CIVITAI_TOKEN found in environment or .env file")
        print("   Add CIVITAI_TOKEN=your_token to .env or export it")
        print("   The download may still work for public models")

    # Prepare download request
    payload = {
        "url": model_url,
        "type": model_type,
        "overwrite": overwrite
    }

    if filename:
        payload["filename"] = filename

    if civitai_token:
        payload["civitai_token"] = civitai_token

    # Submit download request
    download_url = f"{pod_url.rstrip('/')}/download"

    print(f"Downloading from: {model_url}")
    print(f"Pod API: {download_url}")
    print(f"Model type: {model_type}")
    print(f"Filename: {filename or 'auto-detect'}")
    print(f"CivitAI token: {'✅ provided' if civitai_token else '❌ missing'}")

    try:
        response = requests.post(
            download_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=300  # 5 minutes timeout
        )

        if response.status_code == 200:
            result = response.json()
            print("✅ Download successful!")
            print(f"   Saved to: {result.get('path', 'unknown')}")
            print(f"   Size: {result.get('size_mb', 'unknown')} MB")
            return True
        else:
            print(f"❌ Download failed: HTTP {response.status_code}")
            print(f"   Error: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Download failed: {e}")
        return False

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Download models from CivitAI via Pod API")
    parser.add_argument("--pod-url", required=True, help="Pod API URL (e.g. https://abc123-8000.proxy.runpod.net)")
    parser.add_argument("--url", required=True, help="CivitAI model download URL")
    parser.add_argument("--type", required=True, choices=[
        "checkpoints", "loras", "vae", "controlnet", "clip", "clip_vision", "unet", "embeddings"
    ], help="Model type/category")
    parser.add_argument("--filename", help="Custom filename (optional)")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing files")

    args = parser.parse_args()

    success = download_from_civitai(
        pod_url=args.pod_url,
        model_url=args.url,
        model_type=args.type,
        filename=args.filename,
        overwrite=args.overwrite
    )

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()