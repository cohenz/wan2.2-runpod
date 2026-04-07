#!/bin/bash

echo "--- Preparing Network Volume ---"
# Ensure the model directories exist on your volume so ComfyUI doesn't throw errors
mkdir -p /workspace/models/diffusion /workspace/models/checkpoints /workspace/models/wav2vec2 /workspace/models/loras /workspace/models/vae /workspace/models/clip_vision
mkdir -p /workspace/input /workspace/output

echo "Starting ComfyUI..."
cd /app/ComfyUI
# We point the inputs/outputs to the volume, and load the extra paths config
python main.py \
    --listen 127.0.0.1 \
    --port 8188 \
    --extra-model-paths-config extra_model_paths.yaml \
    --input-directory /workspace/input \
    --output-directory /workspace/output &

echo "Starting RunPod Handler..."
cd /app
python -u handler.py
