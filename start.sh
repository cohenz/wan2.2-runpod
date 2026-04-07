#!/bin/bash

echo "Verifying Network Volume..."
if [ ! -d "/workspace/ComfyUI" ]; then
    echo "ERROR: /workspace/ComfyUI not found! The Network Volume is not attached correctly."
    exit 1
fi

# Create local directories for fast I/O (Keeps temp files off your network drive!)
mkdir -p /app/input
mkdir -p /app/output

echo "Starting ComfyUI..."
cd /workspace/ComfyUI

# Boot ComfyUI using the custom paths and local I/O directories
python main.py \
    --listen 127.0.0.1 \
    --port 8188 \
    --extra-model-paths-config /app/extra_model_paths.yaml \
    --input-directory /app/input \
    --output-directory /app/output &

# Safely wait for ComfyUI to fully boot before starting the RunPod handler
echo "Waiting for ComfyUI API..."
until wget -q -O - http://127.0.0.1:8188/system_stats > /dev/null; do
    sleep 2
done
echo "ComfyUI is ready!"

echo "Starting RunPod Handler..."
cd /app
python -u handler.py
