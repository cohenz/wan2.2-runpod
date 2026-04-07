import runpod
import os
import websocket
import json
import uuid
import urllib.request
import time

server_address = "127.0.0.1:8188"
client_id = str(uuid.uuid4())

def wait_for_comfy():
    while True:
        try:
            urllib.request.urlopen(f"http://{server_address}/", timeout=5)
            break
        except:
            time.sleep(2)

def handler(job):
    job_input = job.get("input", {})
    wait_for_comfy()

    # Load Workflow from the file we copied in Dockerfile
    with open("I2V_single.json", 'r') as f:
        workflow = json.load(f)

    # Inject WordPress inputs
    workflow["241"]["inputs"]["positive_prompt"] = job_input.get("prompt", "a man is talking")
    workflow["270"]["inputs"]["value"] = int(job_input.get("frames", 81))
    
    size_str = str(job_input.get("size", "12800720"))
    workflow["245"]["inputs"]["value"] = int(size_str[:4])
    workflow["246"]["inputs"]["value"] = int(size_str[4:])

    if job_input.get("image"):
        img_path = f"/workspace/ComfyUI/input/{uuid.uuid4()}.jpg"
        urllib.request.urlretrieve(job_input.get("image"), img_path)
        workflow["284"]["inputs"]["image"] = os.path.basename(img_path)

    # Execute and wait via WebSocket
    ws = websocket.WebSocket()
    ws.connect(f"ws://{server_address}/ws?clientId={client_id}")
    
    p = {"prompt": workflow, "client_id": client_id}
    data = json.dumps(p).encode('utf-8')
    req = urllib.request.Request(f"http://{server_address}/prompt", data=data)
    prompt_id = json.loads(urllib.request.urlopen(req).read())['prompt_id']

    while True:
        out = ws.recv()
        if isinstance(out, str):
            msg = json.loads(out)
            if msg['type'] == 'executing' and msg['data']['node'] is None:
                break
    ws.close()

    with urllib.request.urlopen(f"http://{server_address}/history/{prompt_id}") as response:
        history = json.loads(response.read())[prompt_id]
        filename = history['outputs']['131']['gifs'][0]['filename']
        
    return {"url": f"https://YOUR_POD_ID-8188.proxy.runpod.net/view?filename={filename}"}

runpod.serverless.start({"handler": handler})
