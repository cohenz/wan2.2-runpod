import runpod
import os
import websocket
import json
import uuid
import urllib.request
import requests
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
            time.sleep(2)

def handler(job):
    job_input = job.get("input", {})
    wait_for_comfy()

# 1. Update directories to match start.sh
    input_dir = "/workspace/input"
    output_dir = "/workspace/output"
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    # 2. Load Workflow
    with open("/app/I2V_single.json", 'r') as f:
        workflow = json.load(f)
    # 3. Map Inputs (Restoring your original logic)
    workflow["241"]["inputs"]["positive_prompt"] = job_input.get("prompt", "a person talking")
    workflow["270"]["inputs"]["value"] = int(job_input.get("frames", 81))
    
    # Restored Size Parsing
    size_str = str(job_input.get("size", "1280720"))
    if size_str == "1280720":
        w, h = 1280, 720
    elif size_str == "7201280":
        w, h = 720, 1280
    elif size_str == "480480":
        w, h = 480, 480
    else:
        w, h = 1280, 720
    
    workflow["245"]["inputs"]["value"] = w
    workflow["246"]["inputs"]["value"] = h

    # 4. Handle Image Download
    image_url = job_input.get("image") or job_input.get("image_url")
    img_name = f"input_{uuid.uuid4()}.png"
    img_path = os.path.join(input_dir, img_name)

    if image_url:
        print(f"Downloading image: {image_url}")
        try:
            opener = urllib.request.build_opener()
            opener.addheaders = [('User-agent', 'Mozilla/5.0')]
            urllib.request.install_opener(opener)
            urllib.request.urlretrieve(image_url, img_path)
            
            # FIX: Change "291" to "284" to inject into the LoadImage node!
            workflow["284"]["inputs"]["image"] = img_name 
        except Exception as e:
            return {"error": f"Failed to download image: {str(e)}"}

    # 5. Queue Prompt and Wait (Websocket logic)
    p = {"prompt": workflow, "client_id": client_id}
    data = json.dumps(p).encode('utf-8')
    req = urllib.request.Request(f"http://{server_address}/prompt", data=data)
    
    try:
        with urllib.request.urlopen(req) as response:
            resp_data = json.loads(response.read().decode('utf-8'))
            prompt_id = resp_data['prompt_id']
    except Exception as e:
        return {"error": f"Failed to queue prompt: {str(e)}"}

    # Polling for completion
    output_filename = None
    while True:
        history_url = f"http://{server_address}/history/{prompt_id}"
        with urllib.request.urlopen(history_url) as response:
            history = json.loads(response.read().decode('utf-8'))
            if prompt_id in history:
                # Get the filename from the SaveVideo/VHS_VideoCombine node
                # Note: node "128" is your sampler, the output is usually node "271" or similar
                # We'll look for the first mp4 output found in history
                for node_id, node_output in history[prompt_id]['outputs'].items():
                    if 'gifs' in node_output:
                        output_filename = node_output['gifs'][0]['filename']
                        break
                break
        time.sleep(2)

    if not output_filename:
        return {"error": "Generation failed or output not found"}

    file_path = os.path.join(output_dir, output_filename)

    # 6. Upload to tmpfiles.org (Restoring your logic)
    upload_url = "https://tmpfiles.org/api/v1/upload"
    try:
        with open(file_path, 'rb') as f:
            files = {'file': (output_filename, f, 'video/mp4')}
            upload_resp = requests.post(upload_url, files=files)
            
        if upload_resp.status_code == 200:
            resp_data = upload_resp.json()
            viewer_url = resp_data.get('data', {}).get('url', '')
            # Restoring your CRITICAL /dl/ swap
            direct_url = viewer_url.replace('tmpfiles.org/', 'tmpfiles.org/dl/')
        else:
            direct_url = None
    except Exception as e:
        return {"error": f"Upload error: {str(e)}"}

    # 7. Cleanup
    if os.path.exists(file_path): os.remove(file_path)
    if os.path.exists(img_path): os.remove(img_path)

    return direct_url

runpod.serverless.start({"handler": handler})
