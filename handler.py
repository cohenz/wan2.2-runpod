import runpod
import os
import json
import uuid
import time
import urllib.request
import requests

SERVER_ADDRESS = "127.0.0.1:8188"
INPUT_DIR = "/app/input"
OUTPUT_DIR = "/app/output"

def download_file(url, save_path):
    response = requests.get(url)
    response.raise_for_status()
    with open(save_path, 'wb') as f:
        f.write(response.content)

def queue_prompt(prompt):
    p = {"prompt": prompt, "client_id": str(uuid.uuid4())}
    data = json.dumps(p).encode('utf-8')
    req = urllib.request.Request(f"http://{SERVER_ADDRESS}/prompt", data=data)
    response = urllib.request.urlopen(req)
    return json.loads(response.read())

def get_history(prompt_id):
    req = urllib.request.Request(f"http://{SERVER_ADDRESS}/history/{prompt_id}")
    response = urllib.request.urlopen(req)
    return json.loads(response.read())

def handler(job):
    job_input = job.get("input", {})
    prompt_text = job_input.get("prompt", "a man is talking")
    frames = int(job_input.get("frames", 81))
    image_url = job_input.get("image_url")
    
    # Optional audio url if your MultiTalk node requires it
    audio_url = job_input.get("audio_url") 

    job_id = job.get("id", str(uuid.uuid4()))
    
    # 1. Download Input Files locally
    img_filename = f"{job_id}.jpg"
    img_path = os.path.join(INPUT_DIR, img_filename)
    if image_url:
        download_file(image_url, img_path)
        
    audio_filename = f"{job_id}.wav"
    audio_path = os.path.join(INPUT_DIR, audio_filename)
    if audio_url:
        download_file(audio_url, audio_path)

    # 2. Load and Modify Workflow
    with open("/app/I2V_single.json", 'r') as f:
        workflow = json.load(f)

    # Update Nodes (Make sure these IDs match your actual JSON file)
    workflow["241"]["inputs"]["positive_prompt"] = prompt_text
    workflow["270"]["inputs"]["value"] = frames
    
    if image_url:
        workflow["291"]["inputs"]["image"] = img_filename
    if audio_url:
        workflow["125"]["inputs"]["audio"] = audio_filename

    # 3. Execute Workflow
    print("Queueing workflow...")
    prompt_response = queue_prompt(workflow)
    prompt_id = prompt_response['prompt_id']

    # 4. Wait for generation to complete
    while True:
        history = get_history(prompt_id)
        if prompt_id in history:
            print("Generation complete!")
            break
        time.sleep(2)

    # 5. Find the output video
    output_files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.mp4')]
    if not output_files:
        raise Exception("Video generation failed: No output file found.")
    
    # Get the most recently created file
    output_files.sort(key=lambda x: os.path.getmtime(os.path.join(OUTPUT_DIR, x)), reverse=True)
    video_path = os.path.join(OUTPUT_DIR, output_files[0])

    # 6. Upload to tmpfiles (as per your original code logic)
    print("Uploading to tmpfiles.org...")
    upload_url = "https://tmpfiles.org/api/v1/upload"
    try:
        with open(video_path, 'rb') as f:
            files = {'file': (output_files[0], f, 'video/mp4')}
            upload_resp = requests.post(upload_url, files=files)
            
        if upload_resp.status_code == 200:
            resp_data = upload_resp.json()
            viewer_url = resp_data.get('data', {}).get('url', '')
            direct_url = viewer_url.replace('tmpfiles.org/', 'tmpfiles.org/dl/')
        else:
            raise Exception("Failed to upload to tmpfiles")
    except Exception as e:
        return {"error": f"Upload failed: {str(e)}"}

    # 7. Cleanup Local Files
    if os.path.exists(img_path): os.remove(img_path)
    if os.path.exists(audio_path): os.remove(audio_path)
    if os.path.exists(video_path): os.remove(video_path)

    return {"video_url": direct_url}

runpod.serverless.start({"handler": handler})
