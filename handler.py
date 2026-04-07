import runpod
import os
import subprocess
import requests
import uuid
import shutil

WAN_REPO_DIR = "/app/Wan2.1"
BASE_MODEL_DIR = "/workspace/models" 

def download_image(url, save_path):
    print(f"Downloading base image from: {url}")
    response = requests.get(url, stream=True, timeout=15)
    if response.status_code == 200:
        with open(save_path, 'wb') as f:
            response.raw.decode_content = True
            shutil.copyfileobj(response.raw, f)
        return True
    return False

def upload_video(file_path):
    print("Uploading video so WordPress can fetch it...")
    # FIX: Use file.io instead of tmpfiles.org to handle larger video files better
    url = "https://file.io"
    try:
        with open(file_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(url, files=files)
        
        if response.status_code == 200:
            download_url = response.json().get('link')
            print(f"Upload successful: {download_url}")
            return download_url
        else:
            print(f"Upload failed: {response.text}")
    except Exception as e:
        print(f"Upload exception: {str(e)}")
    return None

def handler(job):
    job_input = job['input']
    
    task = job_input.get('task', 't2v-14B')
    prompt = job_input.get('prompt', '')
    frames = str(job_input.get('frames', 81))
    sample_steps = str(job_input.get('sample_steps', 50))
    image_url = job_input.get('image', None)
    
    raw_size = str(job_input.get('size', '1280720'))
    if raw_size == "1280720": size = "1280*720"
    elif raw_size == "7201280": size = "720*1280"
    elif raw_size == "19201080": size = "1920*1080"
    elif raw_size == "10801920": size = "1080*1920"
    else: size = "1280*720" 
    
    output_dir = "/tmp/outputs"
    os.makedirs(output_dir, exist_ok=True)
    output_file = f"{output_dir}/output_{uuid.uuid4().hex}.mp4"
    
    model_folder = f"Wan2.1-{task.upper().replace('T2V', 'T2V').replace('I2V', 'I2V')}-720P"
    ckpt_dir = f"{BASE_MODEL_DIR}/{model_folder}"
    
    if not os.path.exists(ckpt_dir):
        return {"error": f"Model directory not found at {ckpt_dir}. Ensure your Network Volume is mounted correctly."}

    cmd = [
        "python", f"{WAN_REPO_DIR}/generate.py",
        "--task", task,
        "--size", size,
        "--ckpt_dir", ckpt_dir,
        "--prompt", prompt,
        "--sample_steps", sample_steps,
        "--offload_model", "True",
        "--save_file", output_file
    ]
    
    if task == "i2v-14B" and image_url:
        img_path = f"/tmp/input_{uuid.uuid4().hex}.png"
        if download_image(image_url, img_path):
            cmd.extend(["--image", img_path])
        else:
            return {"error": "Failed to download the base image from WordPress."}
            
    try:
        print(f"Running command: {' '.join(cmd)}")
        # FIX: Capture the output so RunPod logs show what's happening
        subprocess.run(cmd, check=True, cwd=WAN_REPO_DIR, text=True, capture_output=False)
    except subprocess.CalledProcessError as e:
        return {"error": "Generation failed. Check the RunPod worker logs for the Python traceback."}
        
    if os.path.exists(output_file):
        public_url = upload_video(output_file)
        if public_url:
            return {"url": public_url}
        else:
            return {"error": "Video generated, but failed to upload to temporary storage."}
    else:
        return {"error": "Generation completed but output video was not found."}

if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})
