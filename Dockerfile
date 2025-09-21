# Minimal CUDA + Python base. (Works for Serverless queue workers; not exposing ports.)
FROM nvidia/cuda:12.8.0-cudnn-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl ca-certificates python3 python3-venv python3-pip \
    libgl1 libglib2.0-0 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/app

# Python venv
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# PyTorch (CUDA 12.1 wheels run fine on 12.4 runtime)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
      torch==2.4.0+cu121 torchvision==0.19.0+cu121 \
      --index-url https://download.pytorch.org/whl/cu121

# ComfyUI
RUN git clone --depth=1 https://github.com/comfyanonymous/ComfyUI.git /opt/ComfyUI
RUN pip install --no-cache-dir -r /opt/ComfyUI/requirements.txt

# Server deps
COPY phserver/requirements.txt /opt/app/requirements.txt
RUN pip install --no-cache-dir -r /opt/app/requirements.txt

# Server code
COPY phserver /opt/app/phserver
COPY shared /opt/app/shared
COPY handler.py /opt/app/handler.py

# Where Serverless/Pod volume mounts; point Comfy to it for models
ENV COMFYUI_MODEL_DIR=/workspace/models
ENV PYTHONPATH=/opt/ComfyUI:/opt/app:$PYTHONPATH

# Entrypoint can run either serverless worker or API server for Pod use
COPY phserver/entrypoint.sh /opt/app/entrypoint.sh
RUN chmod +x /opt/app/entrypoint.sh

EXPOSE 8000

CMD ["/opt/app/entrypoint.sh"]
