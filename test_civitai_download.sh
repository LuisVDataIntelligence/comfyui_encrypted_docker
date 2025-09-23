#!/bin/bash

# Test script for downloading WAN 2.1 720P model from CivitAI
# Usage: ./test_civitai_download.sh YOUR_POD_URL

set -e  # Exit on error

POD_URL="$1"
if [ -z "$POD_URL" ]; then
    echo "❌ Error: Pod URL required"
    echo "Usage: $0 https://your-pod-8000.proxy.runpod.net"
    echo ""
    echo "Example:"
    echo "$0 https://abc123-8000.proxy.runpod.net"
    exit 1
fi

# CivitAI model URL for WAN 2.1 720P
CIVITAI_URL="https://civitai.com/api/download/models/2073605?type=Model&format=SafeTensor"

echo "🚀 Testing CivitAI download to Pod..."
echo "Pod URL: $POD_URL"
echo "Model: WAN 2.1 I2V 720P FP16"
echo "Size: ~32GB (this will take a while)"
echo ""

# Test Pod health first
echo "1️⃣ Testing Pod health..."
if curl -f -s "$POD_URL/healthz" >/dev/null; then
    echo "✅ Pod is responding"
    curl -s "$POD_URL/healthz" | python3 -m json.tool
else
    echo "❌ Pod is not responding"
    echo "Make sure your Pod is running with the v1.1.0 image"
    exit 1
fi

echo ""
echo "2️⃣ Starting download..."

# Run the download
python3 client/download_with_civitai.py \
    --pod-url "$POD_URL" \
    --url "$CIVITAI_URL" \
    --type "unet" \
    --filename "wan2.1_i2v_720p_14B_fp16.safetensors"

echo ""
echo "3️⃣ Verifying download..."
echo "Checking if model appears in /models/ls..."

# Check if model was downloaded
curl -s "$POD_URL/models/ls" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    unet_files = data.get('unet', [])
    wan_files = [f for f in unet_files if 'wan' in f.lower()]
    if wan_files:
        print('✅ WAN models found:')
        for f in wan_files:
            print(f'   - {f}')
    else:
        print('❌ No WAN models found in unet directory')
        print('Available unet models:', unet_files)
except:
    print('❌ Failed to parse model list')
"

echo ""
echo "🎉 Test complete!"
echo ""
echo "Next steps:"
echo "1. Update your workflow to use: wan2.1_i2v_720p_14B_fp16.safetensors"
echo "2. Test the workflow with client/submit_job_with_images.py"