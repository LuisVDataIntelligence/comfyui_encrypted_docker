#!/usr/bin/env python3
"""
Enhanced RunPod Serverless client that supports input images.
Supports base64 encoding local images and URL references.
"""

import os, json, base64, requests, sys
from pathlib import Path
import mimetypes

# Allow running from repo root or from the client/ folder
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from shared.crypto_secure import encrypt_for_server

def encode_image_to_base64(image_path: str) -> str:
    """Convert local image file to base64 data URL."""
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    # Detect MIME type
    mime_type, _ = mimetypes.guess_type(str(path))
    if not mime_type or not mime_type.startswith('image/'):
        mime_type = 'image/png'  # default fallback

    # Read and encode
    with open(path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode('utf-8')

    return f"data:{mime_type};base64,{encoded}"

def submit_workflow_with_images(workflow, input_images=None, encrypted=True):
    """
    Submit workflow to RunPod with optional input images.

    Args:
        workflow: ComfyUI workflow dict
        input_images: Dict of {filename: image_data}
            image_data can be:
            - Path to local file (str/Path) - will be base64 encoded
            - URL (str starting with http) - server will download
            - Base64 data URL (str starting with data:)
        encrypted: Whether to encrypt the payload
    """

    # --- Configuration ---
    ENDPOINT_ID = os.getenv("RP_ENDPOINT_ID")
    API_KEY = os.getenv("RP_API_KEY")
    SERVER_PUBLIC_KEY_B64 = os.getenv("SERVER_PUBLIC_KEY_B64")
    RUNSYNC = os.getenv("RP_RUNSYNC", "true").lower() == "true"

    if not ENDPOINT_ID or not API_KEY:
        raise ValueError("Missing RP_ENDPOINT_ID or RP_API_KEY environment variables")

    if encrypted and not SERVER_PUBLIC_KEY_B64:
        raise ValueError("Missing SERVER_PUBLIC_KEY_B64 for encryption")

    # --- Process input images ---
    processed_images = {}
    if input_images:
        for filename, image_data in input_images.items():
            if isinstance(image_data, (str, Path)):
                image_data = str(image_data)
                if image_data.startswith('http'):
                    # URL reference - pass through
                    processed_images[filename] = image_data
                elif image_data.startswith('data:'):
                    # Already base64 encoded
                    processed_images[filename] = image_data
                else:
                    # Local file path - encode to base64
                    processed_images[filename] = encode_image_to_base64(image_data)

    # --- Build payload ---
    payload_data = {
        "workflow": workflow,
        "input_images": processed_images
    }

    if encrypted:
        # Encrypt the entire payload
        encrypted_payload = encrypt_for_server(
            SERVER_PUBLIC_KEY_B64,
            json.dumps(payload_data).encode("utf-8")
        )
        encrypted_payload["encrypted"] = True
        payload = {"input": encrypted_payload}
    else:
        payload = {"input": payload_data}

    # --- Submit to RunPod ---
    url = f"https://api.runpod.ai/v2/{ENDPOINT_ID}/" + ("runsync" if RUNSYNC else "run")
    headers = {
        "authorization": API_KEY,
        "content-type": "application/json",
        "accept": "application/json",
    }

    print(f"Submitting to: {url}")
    print(f"Encrypted: {encrypted}")
    print(f"Images: {list(processed_images.keys()) if processed_images else 'None'}")

    response = requests.post(url, headers=headers, json=payload, timeout=300)

    if response.status_code != 200:
        print(f"Error {response.status_code}: {response.text}")
        return None

    result = response.json()
    print("Response:", json.dumps(result, indent=2))
    return result

if __name__ == "__main__":
    # Example usage
    import argparse

    parser = argparse.ArgumentParser(description="Submit ComfyUI workflow with images to RunPod")
    parser.add_argument("--workflow", required=True, help="Path to workflow JSON file")
    parser.add_argument("--image", action="append", nargs=2, metavar=("filename", "path_or_url"),
                       help="Add input image: --image filename.png /path/to/image.png")
    parser.add_argument("--no-encrypt", action="store_true", help="Send plaintext (for testing)")

    args = parser.parse_args()

    # Load workflow
    with open(args.workflow, "r") as f:
        workflow = json.load(f)

    # Prepare input images
    input_images = {}
    if args.image:
        for filename, path_or_url in args.image:
            input_images[filename] = path_or_url

    # Submit
    result = submit_workflow_with_images(
        workflow=workflow,
        input_images=input_images,
        encrypted=not args.no_encrypt
    )

    if result:
        print("✅ Submission successful!")
    else:
        print("❌ Submission failed!")
        sys.exit(1)