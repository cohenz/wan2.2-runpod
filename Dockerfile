FROM runpod/pytorch:2.2.1-py3.10-cuda12.1.1-devel-ubuntu22.04

USER root

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git wget curl ffmpeg libsm6 libxext6 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install -U "huggingface_hub[hf_transfer]"
ENV HF_HUB_ENABLE_HF_TRANSFER=1

WORKDIR /app

# 1. Install ComfyUI inside the Docker container
RUN git clone https://github.com/comfyanonymous/ComfyUI.git
WORKDIR /app/ComfyUI
RUN pip install --no-cache-dir -r requirements.txt

# 2. Install necessary custom nodes
WORKDIR /app/ComfyUI/custom_nodes
RUN git clone https://github.com/kijai/ComfyUI-WanVideoWrapper.git && \
    cd ComfyUI-WanVideoWrapper && pip install --no-cache-dir -r requirements.txt
RUN git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git
RUN git clone https://github.com/kijai/ComfyUI-MelBandRoFormer.git
RUN git clone https://github.com/kijai/ComfyUI-KJNodes.git

# 3. Install Serverless requirements and specific WanVideo dependencies
WORKDIR /app
RUN pip install flash-attn==2.5.6 --no-build-isolation
RUN pip install --no-cache-dir runpod requests websocket-client librosa boto3 xformers accelerate transformers diffusers

# Copy repo files into the container
COPY handler.py /app/handler.py
COPY I2V_single.json /app/I2V_single.json
COPY extra_model_paths.yaml /app/ComfyUI/extra_model_paths.yaml
COPY start.sh /app/start.sh

RUN chmod +x /app/start.sh
ENV HF_HOME="/workspace/huggingface_cache"

CMD ["/app/start.sh"]
