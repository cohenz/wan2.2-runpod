import runpod
from runpod.serverless.utils import rp_upload
import os
import websocket
import json
import uuid
import urllib.request
import time

server_address = "127.0.0.1:8188"
client_id = str(uuid.uuid4())

def wait_for_comfy():
    print("Waiting for ComfyUI API to become available...")
    while True:
        try:
            urllib.request.urlopen(f"http://{server_address}/", timeout=1)
            print("ComfyUI is ready!")
            break
        except:
            time.sleep(1)

def handler(job):
    job_input = job.get("input", {})
    wait_for_comfy()

    # 1. Ensure required directories exist on your Network Volume
    input_dir = "/workspace/ComfyUI/input"
    output_dir = "/workspace/ComfyUI/output"
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    # 2. Load Workflow
    with open("/app/I2V_single.json", 'r') as f:
        workflow = json.load(f)

    # 3. Inject WordPress inputs securely
    workflow["241"]["inputs"]["positive_prompt"] = job_input.get("prompt", "a man is talking")
    workflow["270"]["inputs"]["value"] = int(job_input.get("frames", 81))
    
    # Safely parse the exact size strings your WP plugin sends
    size_str = str(job_input.get("size", "1280720"))
    if size_str == "1280720":
        w, h = 1280, 720
    elif size_str == "7201280":
        w, h = 720, 1280
    elif size_str == "19201080":
        w, h = 1920, 1080
    elif size_str == "10801920":
        w, h = 1080, 1920
    else:
        w, h = 1280, 720
        
    workflow["245"]["inputs"]["value"] = w
    workflow["246"]["inputs"]["value"] = h

    # 4. Handle Base Image Download (if i2v)
    if job_input.get("image"):
        img_name = f"wp_base_{uuid.uuid4()}.jpg"
        img_path = os.path.join(input_dir, img_name)
        
        # Download image from WordPress to ComfyUI input folder
        req = urllib.request.Request(job_input.get("image"), headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response, open(img_path, 'wb') as out_file:
            out_file.write(response.read())
            
        workflow["284"]["inputs"]["image"] = img_name

    # 5. Execute via WebSocket
    ws = websocket.WebSocket()
    ws.connect(f"ws://{server_address}/ws?clientId={client_id}")
    
    p = {"prompt": workflow, "client_id": client_id}
    data = json.dumps(p).encode('utf-8')
    req = urllib.request.Request(f"http://{server_address}/prompt", data=data)
    prompt_id = json.loads(urllib.request.urlopen(req).read())['prompt_id']

    # Wait for ComfyUI generation to finish
    while True:
        out = ws.recv()
        if isinstance(out, str):
            msg = json.loads(out)
            if msg['type'] == 'executing' and msg['data']['node'] is None:
                break
    ws.close()

    # 6. Fetch the filename and upload to Cloud Storage
    with urllib.request.urlopen(f"http://{server_address}/history/{prompt_id}") as response:
        history = json.loads(response.read())[prompt_id]
        filename = history['outputs']['131']['gifs'][0]['filename']
        file_path = os.path.join(output_dir, filename)
        
    print(f"Generation complete. Uploading {filename}...")
    
    # Upload file using RunPod's built-in utility
    uploaded_url = rp_upload.upload_file_to_bucket(job.get("id"), file_path)

    # Clean up local files on the network volume to prevent filling up disk space
    if os.path.exists(file_path):
        os.remove(file_path)
    if job_input.get("image") and os.path.exists(img_path):
        os.remove(img_path)

    # 7. Return the exact JSON structure your WP plugin expects
    return {"url": uploaded_url}

runpod.serverless.start({"handler": handler})
