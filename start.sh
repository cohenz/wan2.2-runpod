#!/bin/bash

echo "Starting ComfyUI from Network Volume..."
cd /workspace/ComfyUI

# Start ComfyUI in the background on the local port
python main.py --listen 127.0.0.1 --port 8188 &

# Give ComfyUI a few seconds to initialize
sleep 5

echo "Starting RunPod Handler..."
cd /app
python -u handler.py
