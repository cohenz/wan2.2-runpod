import runpod
import os
import subprocess
import requests
import uuid
import shutil

# Paths
WAN_REPO_DIR = "/app/Wan2.1"
# Change this if your network volume structure is different.
# It assumes your models are in /workspace/models/Wan2.1-I2V-14B-720P etc.
BASE_MODEL_DIR = "/workspace/models" 

def download_image(url, save_path):
    print(f"Downloading base image from: {url}")
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(save_path, 'wb') as f:
            response.raw.decode_content = True
            shutil.copyfileobj(response.raw, f)
        return True
    return False

def upload_video(file_path):
    """Uploads the video to a temporary public host so WordPress can download it."""
    print("Uploading video so WordPress can fetch it...")
    url = "https://tmpfiles.org/api/v1/upload"
    try:
        with open(file_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(url, files=files)
        
        if response.status_code == 200:
            # tmpfiles returns: {"data": {"url": "https://tmpfiles.org/12345/video.mp4"}}
            # We change it to the direct download link: https://tmpfiles.org/dl/12345/video.mp4
            download_url = response.json()['data']['url'].replace('tmpfiles.org/', 'tmpfiles.org/dl/')
            print(f"Upload successful: {download_url}")
            return download_url
    except Exception as e:
        print(f"Upload failed: {str(e)}")
    return None

def handler(job):
    job_input = job['input']
    
    # 1. Parse the payload sent from WordPress
    task = job_input.get('task', 't2v-14B')
    prompt = job_input.get('prompt', '')
    frames = str(job_input.get('frames', 81))
    sample_steps = str(job_input.get('sample_steps', 50))
    image_url = job_input.get('image', None)
    
    # Fix the size string from WordPress (WP sends "1280720", Wan needs "1280*720")
    raw_size = str(job_input.get('size', '1280720'))
    if raw_size == "1280720": size = "1280*720"
    elif raw_size == "7201280": size = "720*1280"
    elif raw_size == "19201080": size = "1920*1080"
    elif raw_size == "10801920": size = "1080*1920"
    else: size = "1280*720" # fallback
    
    # 2. Prepare directories and files
    output_dir = "/tmp/outputs"
    os.makedirs(output_dir, exist_ok=True)
    output_file = f"{output_dir}/output_{uuid.uuid4().hex}.mp4"
    
    # Construct the model path based on the task (i2v vs t2v)
    model_folder = f"Wan2.1-{task.upper().replace('T2V', 'T2V').replace('I2V', 'I2V')}-720P"
    ckpt_dir = f"{BASE_MODEL_DIR}/{model_folder}"
    
    # 3. Build the CLI command exactly how you ran it manually
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
    
    # Add image to command if it's Image-to-Video
    if task == "i2v-14B" and image_url:
        img_path = f"/tmp/input_{uuid.uuid4().hex}.png"
        if download_image(image_url, img_path):
            cmd.extend(["--image", img_path])
        else:
            return {"error": "Failed to download the base image from WordPress."}
            
    # 4. Run the Wan generation
    try:
        print(f"Running generation command...")
        subprocess.run(cmd, check=True, cwd=WAN_REPO_DIR)
    except subprocess.CalledProcessError as e:
        return {"error": f"Generation failed. Error: {str(e)}"}
        
    # 5. Upload and return the URL
    if os.path.exists(output_file):
        public_url = upload_video(output_file)
        if public_url:
            # This perfectly matches what WordPress expects: $status_response['output']['url']
            return {"url": public_url}
        else:
            return {"error": "Video generated, but failed to upload to temporary storage."}
    else:
        return {"error": "Generation completed but the output video file was not found."}

if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})
