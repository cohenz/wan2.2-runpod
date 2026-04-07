# Use the same base as your working version for consistency
FROM runpod/pytorch:2.2.1-py3.10-cuda12.1.1-devel-ubuntu22.04

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git wget ffmpeg libsm6 libxext6 \
    && rm -rf /var/lib/apt/lists/*

# High-speed HuggingFace downloads
RUN pip install -U "huggingface_hub[hf_transfer]"
ENV HF_HUB_ENABLE_HF_TRANSFER=1

WORKDIR /app

# Clone Wan2.1
RUN git clone https://github.com/Wan-Video/Wan2.1.git
WORKDIR /app/Wan2.1
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir runpod requests

# --- DOWNLOAD MODELS HERE ---
# We create the folder structure your handler expects
RUN mkdir -p /workspace/models/Wan2.1-T2V-14B-720P
RUN mkdir -p /workspace/models/Wan2.1-I2V-14B-720P

# Example: Downloading T2V 14B Weights (Adjust URLs/filenames to match Wan2.1 official HF)
# Note: You need to download the actual model files into these directories.
# RUN huggingface-cli download Wan-Video/Wan2.1-T2V-14B --local-dir /workspace/models/Wan2.1-T2V-14B-720P

COPY handler.py /app/handler.py
WORKDIR /app

CMD ["python", "-u", "handler.py"]
