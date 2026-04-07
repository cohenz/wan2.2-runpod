FROM runpod/pytorch:2.2.1-py3.10-cuda12.1.1-devel-ubuntu22.04

RUN apt-get update && apt-get install -y \
    git wget ffmpeg libsm6 libxext6 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install -U "huggingface_hub[hf_transfer]"
ENV HF_HUB_ENABLE_HF_TRANSFER=1

WORKDIR /app

# Clone Wan2.1
RUN git clone https://github.com/Wan-Video/Wan2.1.git
WORKDIR /app/Wan2.1

# FIX 1: Install flash-attn without build isolation to prevent the 1-hour hang
RUN pip install flash-attn==2.5.6 --no-build-isolation
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir runpod requests

COPY handler.py /app/handler.py
WORKDIR /app

# FIX 2: Force HuggingFace to cache the 15GB of text encoders to your Network Volume
# so it doesn't download them every time a pod wakes up.
ENV HF_HOME="/workspace/huggingface_cache"

CMD ["python", "-u", "handler.py"]
