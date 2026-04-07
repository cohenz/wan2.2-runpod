FROM runpod/pytorch:2.2.1-py3.10-cuda12.1.1-devel-ubuntu22.04

RUN apt-get update && apt-get install -y \
    git wget ffmpeg libsm6 libxext6 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install -U "huggingface_hub[hf_transfer]"
ENV HF_HUB_ENABLE_HF_TRANSFER=1

WORKDIR /app

# Install dependencies for the handler
RUN pip install --no-cache-dir runpod requests websocket-client librosa

# Clone Wan2.1 and install its requirements
RUN git clone https://github.com/Wan-Video/Wan2.1.git
WORKDIR /app/Wan2.1
RUN pip install flash-attn==2.5.6 --no-build-isolation
RUN pip install --no-cache-dir -r requirements.txt

WORKDIR /app
# COPY all necessary files from your Git repo to the container
COPY handler.py /app/handler.py
COPY I2V_single.json /app/I2V_single.json
COPY requirements.txt /app/requirements.txt

# FIX: Ensure HF caches to the network volume
ENV HF_HOME="/workspace/huggingface_cache"

# Start the handler
CMD ["python", "-u", "handler.py"]
