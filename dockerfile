# Minimal CUDA + Python base. (Works for Serverless queue workers; not exposing ports.)
FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl ca-certificates python3 python3-venv python3-pip \
    libgl1 libglib2.0-0 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# Python venv
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# PyTorch (CUDA 12.1 wheels run fine on 12.4 runtime)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
      torch==2.4.0+cu121 torchvision==0.19.0+cu121 \
      --index-url https://download.pytorch.org/whl/cu121

# ComfyUI
RUN git clone --depth=1 https://github.com/comfyanonymous/ComfyUI.git /workspace/ComfyUI
RUN pip install --no-cache-dir -r /workspace/ComfyUI/requirements.txt

# Worker deps
COPY requirements.txt /workspace/requirements.txt
RUN pip install --no-cache-dir -r /workspace/requirements.txt

# Worker code
COPY handler.py comfy_client.py crypto_secure.py /workspace/
COPY examples /workspace/examples

# Where Serverless network volume mounts; point Comfy to it for models
ENV COMFYUI_MODEL_DIR=/runpod-volume/models
ENV PYTHONPATH=/workspace/ComfyUI:$PYTHONPATH

# Start the worker (RunPod serverless handler)
CMD ["python3", "/workspace/handler.py"]