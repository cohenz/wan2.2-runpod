#!/bin/bash

echo "--- Waiting for Network Volume ---"
# Wait up to 60 seconds for the RunPod network volume to attach
# Serverless endpoints mount network volumes at /runpod-volume, NOT /workspace
MAX_RETRIES=30
count=0
COMFY_PATH=""

while [ -z "$COMFY_PATH" ]; do
    # Check the root of the network volume
    if [ -d "/runpod-volume/ComfyUI" ]; then
        COMFY_PATH="/runpod-volume/ComfyUI"
    # Fallback just in case you placed it inside a 'workspace' subfolder on the drive
    elif [ -d "/runpod-volume/workspace/ComfyUI" ]; then
        COMFY_PATH="/runpod-volume/workspace/ComfyUI"
    else
        echo "Waiting for Network Volume to mount... ($count/$MAX_RETRIES)"
        sleep 2
        count=$((count+1))
        if [ $count -ge $MAX_RETRIES ]; then
            echo "ERROR: Network volume did not mount at /runpod-volume/ComfyUI."
            exit 1
        fi
    fi
done

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
