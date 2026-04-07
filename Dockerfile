FROM runpod/pytorch:2.2.1-py3.10-cuda12.1.1-devel-ubuntu22.04

USER root

# 1. Install system dependencies (Ensures 'git' is in the $PATH)
RUN apt-get update && apt-get install -y \
    git wget curl ffmpeg libsm6 libxext6 \
    && rm -rf /var/lib/apt/lists/*

# 2. HuggingFace configuration
RUN pip install --no-cache-dir -U "huggingface_hub[hf_transfer]"
ENV HF_HUB_ENABLE_HF_TRANSFER=1

# 3. Install Serverless & Audio Requirements (No cache to save space)
RUN pip install --no-cache-dir runpod requests websocket-client librosa boto3 soundfile

# 4. Install flash-attn
RUN pip install --no-cache-dir flash-attn==2.5.6 --no-build-isolation

# 5. CRITICAL FIX: Pin xformers to 0.0.25 to maintain PyTorch 2.2.1 compatibility.
# This prevents pip from upgrading to Torch 2.11.0 and pulling heavy CUDA 13 binaries.
RUN pip install --no-cache-dir xformers==0.0.25 accelerate transformers diffusers

# 6. Additional node dependencies
RUN pip install --no-cache-dir aiohttp kornia safetensors einops scipy

WORKDIR /app

# 7. Copy handler and configurations
COPY handler.py /app/handler.py
COPY I2V_single.json /app/I2V_single.json
COPY extra_model_paths.yaml /app/extra_model_paths.yaml
COPY start.sh /app/start.sh

RUN chmod +x /app/start.sh

# Move HF cache to network volume to avoid downloading models on every cold start
ENV HF_HOME="/runpod-volume/huggingface_cache"

CMD ["/app/start.sh"]
