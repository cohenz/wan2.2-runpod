#!/bin/bash

echo "--- Waiting for Network Volume ---"
# Wait up to 60 seconds for the RunPod network volume to attach
MAX_RETRIES=30
count=0
while [ ! -d "/workspace/ComfyUI" ]; do
    echo "Waiting for /workspace/ComfyUI to mount... ($count/$MAX_RETRIES)"
    sleep 2
    count=$((count+1))
    if [ $count -ge $MAX_RETRIES ]; then
        echo "ERROR: Network volume did not mount at /workspace/ComfyUI."
        exit 1
    fi
done

COMFY_PATH="/workspace/ComfyUI"
echo "Found ComfyUI at: $COMFY_PATH"

# Setup local folders for fast I/O and isolation from the other endpoint
mkdir -p /app/input /app/output /app/user

# Start ComfyUI using the Docker container's Python environment
cd $COMFY_PATH
python main.py \
    --listen 127.0.0.1 \
    --port 8188 \
    --extra-model-paths-config /app/extra_model_paths.yaml \
    --input-directory /app/input \
    --output-directory /app/output \
    --user-directory /app/user &

# Wait briefly to ensure ComfyUI starts initializing
sleep 5

# Start the RunPod Handler
echo "Starting RunPod Handler..."
cd /app
python -u handler.py
