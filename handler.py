import runpod
import os
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

    # Use local ephemeral directories to prevent shared volume conflicts
    input_dir = "/app/input"
    output_dir = "/app/output"
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    with open("/app/I2V_single.json", 'r') as f:
        workflow = json.load(f)

    # Map Inputs
    workflow["241"]["inputs"]["positive_prompt"] = job_input.get("prompt", "a person talking")
    workflow["270"]["inputs"]["value"] = int(job_input.get("frames", 81))
    
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

    # Handle Image Download
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
            workflow["291"]["inputs"]["image"] = img_name
        except Exception as e:
            return {"error": f"Failed to download image: {str(e)}"}

    # Queue Prompt
    p = {"prompt": workflow, "client_id": client_id}
    data = json.dumps(p).encode('utf-8')
    req = urllib.request.Request(f"http://{server_address}/prompt", data=data)
    
    try:
        with urllib.request.urlopen(req) as response:
            resp_data = json.loads(response.read().decode('utf-8'))
            prompt_id = resp_data['prompt_id']
    except Exception as e:
        return {"error": f"Failed to queue prompt: {str(e)}"}

    # Poll for completion
    output_filename = None
    while True:
        history_url = f"http://{server_address}/history/{prompt_id}"
        try:
            with urllib.request.urlopen(history_url) as response:
                history = json.loads(response.read().decode('utf-8'))
                if prompt_id in history:
                    outputs = history[prompt_id].get('outputs', {})
                    for node_id, node_output in outputs.items():
                        if 'gifs' in node_output:
                            output_filename = node_output['gifs'][0]['filename']
                            break
                        elif 'images' in node_output:
                            output_filename = node_output['images'][0]['filename']
                            break
                    break
        except Exception:
            pass
        time.sleep(2)

    if not output_filename:
        return {"error": "Generation failed or output not found"}

    file_path = os.path.join(output_dir, output_filename)

    if not os.path.exists(file_path):
        return {"error": f"File {output_filename} not generated correctly."}

    # Upload to tmpfiles.org
    upload_url = "https://tmpfiles.org/api/v1/upload"
    direct_url = None
    try:
        with open(file_path, 'rb') as f:
            files = {'file': (output_filename, f, 'video/mp4')}
            upload_resp = requests.post(upload_url, files=files)
            
        if upload_resp.status_code == 200:
            resp_data = upload_resp.json()
            viewer_url = resp_data.get('data', {}).get('url', '')
            direct_url = viewer_url.replace('tmpfiles.org/', 'tmpfiles.org/dl/')
    except Exception as e:
        return {"error": f"Upload error: {str(e)}"}
    finally:
        if os.path.exists(file_path): os.remove(file_path)
        if os.path.exists(img_path): os.remove(img_path)

    return direct_url

runpod.serverless.start({"handler": handler})
