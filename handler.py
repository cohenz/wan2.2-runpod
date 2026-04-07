import runpod
import os
import websocket
import base64
import json
import uuid
import logging
import urllib.request
import urllib.parse
import binascii
import subprocess
import shutil
import time

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

server_address = os.getenv("SERVER_ADDRESS", "127.0.0.1")
client_id = str(uuid.uuid4())

# --- KEEP YOUR EXISTING HELPER FUNCTIONS HERE (download_file_from_url, get_videos, etc.) ---

def handler(job):
    job_input = job.get("input", {})
    
    # 1. Map WordPress Plugin Inputs
    wp_task = job_input.get("task", "i2v-14B")
    wp_prompt = job_input.get("prompt", "A person talking naturally")
    wp_frames = job_input.get("frames", 81)
    wp_steps = job_input.get("sample_steps", 30)
    wp_image_url = job_input.get("image")
    wp_size_str = str(job_input.get("size", "1280720"))

    # 2. FIXED Resolution Parsing Logic
    if len(wp_size_str) == 8: # e.g., 19201080
        width, height = int(wp_size_str[:4]), int(wp_size_str[4:])
    elif len(wp_size_str) == 7:
        if wp_size_str.startswith("720"): # 7201280
            width, height = 720, 1280
        else: # 1280720
            width, height = 1280, 720
    else:
        width, height = 1280, 720

    logger.info(f"🚀 Processing: {wp_task} | {width}x{height} | {wp_frames} frames")

    task_id = f"task_{uuid.uuid4()}"
    
    # 3. Handle Image Input
    media_path = "/examples/image.jpg" 
    if wp_task == "i2v-14B" and wp_image_url:
        try:
            media_path = download_file_from_url(wp_image_url, f"/tmp/{task_id}_input.jpg")
        except Exception as e:
            return {"error": f"Failed to download image: {str(e)}"}

    # 4. Load Workflow
    workflow_path = "/I2V_single.json" 
    try:
        with open(workflow_path, 'r') as f:
            prompt = json.load(f)
    except Exception as e:
        return {"error": f"Failed to load workflow file: {str(e)}"}

    # 5. Inject Values into ComfyUI Nodes
    try:
        if "241" in prompt: prompt["241"]["inputs"]["positive_prompt"] = wp_prompt
        if "245" in prompt: prompt["245"]["inputs"]["value"] = width
        if "246" in prompt: prompt["246"]["inputs"]["value"] = height
        if "270" in prompt: prompt["270"]["inputs"]["value"] = wp_frames
        if wp_task == "i2v-14B" and "284" in prompt:
            prompt["284"]["inputs"]["image"] = media_path
            
        # IMPORTANT: Fix the Model Path if it's currently hardcoded to /workspace/
        # You can force it here if you know your volume mount path:
        # if "YOUR_MODEL_NODE_ID" in prompt:
        #    prompt["ID"]["inputs"]["model_path"] = "/runpod-volume/models/Wan2.1-I2V-14B-720P"

    except KeyError as e:
        logger.warning(f"⚠️ Node ID not found: {e}")

    # 6. Execution via WebSocket
    try:
        ws = websocket.WebSocket()
        ws.connect(f"ws://{server_address}:8188/ws?clientId={client_id}")
        videos = get_videos(ws, prompt, "image", "single") # Ensure this helper exists
        ws.close()
    except Exception as e:
        return {"error": f"ComfyUI Connection Error: {str(e)}"}

    # 7. Return Result
    output_video_path = None
    for node_id in videos:
        if videos[node_id]:
            output_video_path = videos[node_id][0]
            break

    if output_video_path and os.path.exists(output_video_path):
        output_filename = f"out_{task_id}.mp4"
        final_volume_path = f"/runpod-volume/{output_filename}"
        shutil.copy2(output_video_path, final_volume_path)
        
        # Note: WordPress needs a public URL. Use an S3 upload or similar here.
        return {"url": f"https://your-public-storage.com/{output_filename}"} 
    else:
        return {"error": "Video generation failed or output not found."}

runpod.serverless.start({"handler": handler})
