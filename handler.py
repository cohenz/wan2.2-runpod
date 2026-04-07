import runpod
import os
import websocket
import json
import uuid
import logging
import urllib.request
import shutil
import time

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

server_address = "127.0.0.1:8188"
client_id = str(uuid.uuid4())

def download_file(url, save_path):
    logger.info(f"Downloading: {url}")
    with urllib.request.urlopen(url) as response, open(save_path, 'wb') as out_file:
        shutil.copyfileobj(response, out_file)
    return save_path

def get_video_path(ws, prompt):
    # Queue the job
    p = {"prompt": prompt, "client_id": client_id}
    data = json.dumps(p).encode('utf-8')
    req = urllib.request.Request(f"http://{server_address}/prompt", data=data)
    with urllib.request.urlopen(req) as response:
        prompt_id = json.loads(response.read())['prompt_id']

    # Wait for completion
    while True:
        out = ws.recv()
        if isinstance(out, str):
            message = json.loads(out)
            if message['type'] == 'executing':
                data = message['data']
                if data['node'] is None and data['prompt_id'] == prompt_id:
                    break
        else: continue

    # Find the output file
    history_url = f"http://{server_address}/history/{prompt_id}"
    with urllib.request.urlopen(history_url) as response:
        history = json.loads(response.read())[prompt_id]
        
    # Get the file path from the output node (Node 131 in your workflow)
    for node_id in history['outputs']:
        node_output = history['outputs'][node_id]
        if 'gifs' in node_output: # VHS_VideoCombine uses 'gifs' key for videos
            return node_output['gifs'][0]['filename']
    return None

def handler(job):
    job_input = job.get("input", {})
    
    # 1. Map WordPress Inputs
    wp_prompt = job_input.get("prompt", "a man is talking")
    wp_image_url = job_input.get("image")
    wp_size_str = str(job_input.get("size", "1280720"))
    wp_frames = int(job_input.get("frames", 81))

    # 2. Parse Resolution (e.g., "1280720" -> 1280, 720)
    if len(wp_size_str) == 8: # 10801920
        width, height = int(wp_size_str[:4]), int(wp_size_str[4:])
    else: # 1280720
        width, height = int(wp_size_str[:4]), int(wp_size_str[4:])

    # 3. Load Workflow
    try:
        with open("I2V_single.json", 'r') as f:
            workflow = json.load(f)
    except Exception as e:
        return {"error": f"Workflow file missing: {str(e)}"}

    # 4. Inject Values into Workflow Nodes
    # Using the IDs from your provided JSON snippet
    workflow["241"]["inputs"]["positive_prompt"] = wp_prompt
    workflow["245"]["inputs"]["value"] = width
    workflow["246"]["inputs"]["value"] = height
    workflow["270"]["inputs"]["value"] = wp_frames

    # Handle Image
    if wp_image_url:
        local_img = download_file(wp_image_url, "/tmp/input_image.jpg")
        workflow["284"]["inputs"]["image"] = local_img

    # 5. Execute in ComfyUI
    try:
        ws = websocket.WebSocket()
        ws.connect(f"ws://{server_address}/ws?clientId={client_id}")
        video_filename = get_video_path(ws, workflow)
        ws.close()
    except Exception as e:
        return {"error": f"ComfyUI Error: {str(e)}"}

    # 6. Return Result
    if video_filename:
        # Move output to a persistent location or return the internal path
        # Note: Adjust path based on where ComfyUI saves outputs
        output_path = f"/workspace/ComfyUI/output/{video_filename}"
        return {"url": output_path} 
    
    return {"error": "Generation failed."}

runpod.serverless.start({"handler": handler})
