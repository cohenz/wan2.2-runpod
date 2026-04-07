FROM runpod/pytorch:2.2.1-py3.10-cuda12.1.1-devel-ubuntu22.04

USER root

# Install system dependencies for audio/video processing and downloading
RUN apt-get update && apt-get install -y \
    git wget ffmpeg libsm6 libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Install the Python environment requirements
RUN pip install -U "huggingface_hub[hf_transfer]"
ENV HF_HUB_ENABLE_HF_TRANSFER=1

# Install RunPod Serverless SDK and other handler requirements
RUN pip install --no-cache-dir runpod requests websocket-client librosa boto3

# Install heavy dependencies that Wan2.2 custom nodes require
RUN pip install flash-attn==2.5.6 --no-build-isolation
RUN pip install xformers accelerate transformers diffusers

WORKDIR /app

# Copy our RunPod worker files
COPY handler.py /app/handler.py
COPY I2V_single.json /app/I2V_single.json
COPY start.sh /app/start.sh

# Make the start script executable
RUN chmod +x /app/start.sh

# Ensure HuggingFace caches to the network volume so it doesn't eat container disk space
ENV HF_HOME="/workspace/huggingface_cache"

# Start script boots ComfyUI in the background, then runs the handler
CMD ["/app/start.sh"]
