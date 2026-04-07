#!/bin/bash

echo "--- Debugging Network Volume ---"
ls -d /workspace/*/ 2>/dev/null || echo "/workspace is empty or not mounted"

# 1. Find where ComfyUI actually is
if [ -d "/workspace/ComfyUI" ]; then
    COMFY_PATH="/workspace/ComfyUI"
elif [ -f "/workspace/main.py" ]; then
    COMFY_PATH="/workspace"
else
    echo "ERROR: Could not find ComfyUI or main.py in /workspace. Check your RunPod Volume attachment."
    exit 1
fi

echo "Found ComfyUI at: $COMFY_PATH"

# 2. Setup local folders for fast I/O (prevents network drive lag)
mkdir -p /app/input /app/output

# 3. Start ComfyUI
cd $COMFY_PATH
python main.py \
    --listen 127.0.0.1 \
    --port 8188 \
    --extra-model-paths-config /app/extra_model_paths.yaml \
    --input-directory /app/input \
    --output-directory /app/output &

# 4. Start the RunPod Handler
echo "Starting RunPod Handler..."
cd /app
python -u handler.py
