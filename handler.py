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
import librosa
import shutil
import time

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

server_address = os.getenv("SERVER_ADDRESS", "127.0.0.1")
client_id = str(uuid.uuid4())

# --- KEEP ALL YOUR EXISTING HELPER FUNCTIONS (download_file_from_url, get_videos, etc.) ---
# [I am omitting the middle helper functions for brevity, keep them exactly as they are in your working file]

def handler(job):
    job_input = job.get("input", {})
    
    # 1. BRIDGE: Map WordPress Plugin Inputs to ComfyUI Variables
    # WordPress sends: task, prompt, frames, sample_steps, image (url), size
    wp_task = job_input.get("task", "i2v-14B")  # 't2v-14B' or 'i2v-14B'
    wp_prompt = job_input.get("prompt", "A person talking naturally")
    wp_frames = job_input.get("frames", 81)
    wp_steps = job_input.get("sample_steps", 30)
    wp_image_url = job_input.get("image")
    wp_size_str = str(job_input.get("size", "1280720")) # e.g. "1280720"

    # 2. Parse Resolution
    # WordPress sends "1280720" -> we need 1280 and 720
    if len(wp_size_str) == 7: # 7201280
        width, height = int(wp_size_str[:3]), int(wp_size_str[3:])
    else: # 1280720
        width, height = int(wp_size_str[:4]), int(wp_size_str[4:])

    logger.info(f"🚀 WP Job Received: Task={wp_task}, Size={width}x{height}, Frames={wp_frames}")

    task_id = f"task_{uuid.uuid4()}"
    
    # 3. Handle Image Input (only if I2V)
    media_path = "/examples/image.jpg" # Default
    if wp_task == "i2v-14B" and wp_image_url:
        try:
            media_path = download_file_from_url(wp_image_url, f"/tmp/{task_id}_input.jpg")
        except Exception as e:
            return {"error": f"Failed to download image from WordPress: {str(e)}"}

    # 4. Set Workflow Path 
    # Adapting to your existing files. Note: T2V might need its own .json 
    # if you haven't made one yet, but we'll use your I2V_single as the base.
    workflow_path = "/I2V_single.json" 
    prompt = load_workflow(workflow_path)

    # 5. Inject Values into ComfyUI Nodes
    # We use the IDs from your working handler.py
    try:
        # Set Prompt
        if "241" in prompt: prompt["241"]["inputs"]["positive_prompt"] = wp_prompt
        
        # Set Resolution
        if "245" in prompt: prompt["245"]["inputs"]["value"] = width
        if "246" in prompt: prompt["246"]["inputs"]["value"] = height
        
        # Set Frame Count
        if "270" in prompt: prompt["270"]["inputs"]["value"] = wp_frames

        # Set Image (only for I2V)
        if wp_task == "i2v-14B" and "284" in prompt:
            prompt["284"]["inputs"]["image"] = media_path

        # Set Sampling Steps (Finding the Sampler node)
        sampler_id = "128" # Based on your previous handler's preferred_id
        if sampler_id in prompt:
            prompt[sampler_id]["inputs"]["steps"] = wp_steps
            # Ensure force_offload is True to save VRAM on RunPod
            prompt[sampler_id]["inputs"]["force_offload"] = True

    except KeyError as e:
        logger.warning(f"⚠️ Could not find expected node ID in workflow: {e}")

    # 6. Execution (WebSocket Logic)
    # [This part remains largely identical to your working code]
    try:
        # Check HTTP
        urllib.request.urlopen(f"http://{server_address}:8188/", timeout=5)
        
        ws = websocket.WebSocket()
        ws.connect(f"ws://{server_address}:8188/ws?clientId={client_id}")
        
        # Note: input_type and person_count are passed to your existing get_videos function
        videos = get_videos(ws, prompt, "image", "single")
        ws.close()
    except Exception as e:
        return {"error": f"ComfyUI Connection Error: {str(e)}"}

    # 7. Return Result to WordPress
    output_video_path = None
    for node_id in videos:
        if videos[node_id]:
            output_video_path = videos[node_id][0]
            break

    if output_video_path and os.path.exists(output_video_path):
        # We need to get this file to a URL WordPress can reach.
        # If using Network Volume, copy it there:
        output_filename = f"out_{task_id}.mp4"
        final_volume_path = f"/runpod-volume/{output_filename}"
        shutil.copy2(output_video_path, final_volume_path)
        
        # IMPORTANT: RunPod Serverless 'output' needs to return the URL or Path
        # The WordPress plugin expects a field it can use to download the file.
        return {"url": final_volume_path} 
    else:
        return {"error": "Video generation failed or output not found."}

runpod.serverless.start({"handler": handler})
