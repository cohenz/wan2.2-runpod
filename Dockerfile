# Use an official PyTorch base image with CUDA support
FROM runpod/pytorch:2.2.1-py3.10-cuda12.1.1-devel-ubuntu22.04

# Install basic system utilities required for video processing
RUN apt-get update && apt-get install -y \
    git \
    wget \
    ffmpeg \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Set up the working directory
WORKDIR /app

# Clone the official Wan2.1 repository
RUN git clone https://github.com/Wan-Video/Wan2.1.git

# Install Wan's Python dependencies
WORKDIR /app/Wan2.1
RUN pip install --no-cache-dir -r requirements.txt

# Install specific packages needed for our RunPod handler
RUN pip install --no-cache-dir runpod requests

# Copy your custom handler code into the container
COPY handler.py /app/handler.py

# Set the working directory back to /app where the handler lives
WORKDIR /app

# Tell RunPod what script to run when the pod wakes up
CMD ["python", "handler.py"]
