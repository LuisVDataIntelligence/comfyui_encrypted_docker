#!/bin/bash

# Download script for WAN Image-to-Video workflow models
# Set your Pod URL before running
POD_URL="${POD_URL:-https://your-pod-url}"

echo "Downloading models for WAN I2V workflow to: $POD_URL"

# Function to download with error handling
download_model() {
    local url="$1"
    local type="$2"
    local filename="$3"
    local dest="$4"

    echo "Downloading $filename to $type/$dest..."

    curl -X POST "$POD_URL/download" \
        -H "Content-Type: application/json" \
        -d "{
            \"url\": \"$url\",
            \"type\": \"$type\",
            \"filename\": \"$filename\",
            \"dest\": \"$dest\"
        }" \
        -w "HTTP %{http_code} - Time: %{time_total}s\n"

    sleep 2  # Brief pause between downloads
}

echo "=== Downloading UNet/Diffusion Models ==="
# WAN 2.1 I2V 14B model - you'll need to find the actual download URL
# This is likely from HuggingFace or a similar model repository
download_model "https://huggingface.co/WAN-AI/WAN2.1-I2V-14B/resolve/main/wan2.1_i2v_480p_14B_fp16.safetensors" \
    "unet" "wan2.1_i2v_480p_14B_fp16.safetensors" ""

echo "=== Downloading CLIP Models ==="
# UMT5 XXL CLIP model
download_model "https://huggingface.co/WAN-AI/UMT5-XXL/resolve/main/umt5_xxl_fp16.safetensors" \
    "clip" "umt5_xxl_fp16.safetensors" ""

echo "=== Downloading VAE Models ==="
# WAN 2.1 VAE
download_model "https://huggingface.co/WAN-AI/WAN2.1-VAE/resolve/main/wan_2.1_vae.safetensors" \
    "vae" "wan_2.1_vae.safetensors" ""

echo "=== Downloading CLIP Vision ==="
# CLIP Vision H model
download_model "https://huggingface.co/laion/CLIP-ViT-H-14-laion2B-s32B-b79K/resolve/main/open_clip_pytorch_model.bin" \
    "clip_vision" "clip_vision_h.safetensors" ""

echo "=== Downloading LoRA Models ==="
# Main WAN I2V LoRA
download_model "https://huggingface.co/WAN-AI/WAN2.1-I2V-LoRA/resolve/main/Wan2.1_I2V_14B_FusionX_LoRA.safetensors" \
    "loras" "Wan2.1_I2V_14B_FusionX_LoRA.safetensors" ""

# High speed dynamic LoRA
download_model "https://huggingface.co/WAN-AI/LoRA-Collection/resolve/main/High_speed_dynamic_-_v0-1.safetensors" \
    "loras" "High_speed_dynamic_-_v0-1.safetensors" "WAN/"

# NSFW Posing LoRA
download_model "https://huggingface.co/WAN-AI/LoRA-Collection/resolve/main/Wan_NSFW_Posing_Nude_-_i2v_720p_v1-0.safetensors" \
    "loras" "Wan_NSFW_Posing_Nude_-_i2v_720p_v1-0.safetensors" "WAN/Test/"

# Secret Sauce LoRA
download_model "https://huggingface.co/WAN-AI/LoRA-Collection/resolve/main/SECRET_SAUCE_WAN_2-1_-_v1-0.safetensors" \
    "loras" "SECRET_SAUCE_WAN_2-1_-_v1-0.safetensors" "WAN/"

# Lightx2v distilled LoRA
download_model "https://huggingface.co/WAN-AI/LoRA-Collection/resolve/main/Wan21_I2V_14B_lightx2v_cfg_step_distill_lora_rank128_bf16.safetensors" \
    "loras" "Wan21_I2V_14B_lightx2v_cfg_step_distill_lora_rank128_bf16.safetensors" ""

echo "=== Downloading Video Processing Models ==="
# FILM VFI model
download_model "https://github.com/google-research/frame-interpolation/releases/download/v1.0/film_net_fp32.pt" \
    "vfi" "film_net_fp32.pt" ""

echo "=== Download Complete ==="
echo "Checking model directory..."
curl -s "$POD_URL/models/ls" | jq . || echo "Models list request failed"

echo ""
echo "To use this script:"
echo "1. Set POD_URL environment variable: export POD_URL=https://your-pod-url"
echo "2. Run: bash download_workflow_models.sh"
echo ""
echo "Note: Some URLs may need adjustment based on actual model repositories"