import requests
import dotenv
import os

dotenv.load_dotenv()

IMAGE_MODEL = os.getenv("IMAGE_MODEL") or ''
IMAGE_MODEL_KEY = os.getenv("IMAGE_MODEL_KEY") or ''
API_URL = os.getenv("IMAGE_API_BASE") or ''

def generate_image(prompt="", negative_prompt=None, save_path: str = '.'):
    dir_name = os.path.dirname(save_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    
    if not prompt:
        raise ValueError("Prompt must not be empty.")

    payload = {
        "model": IMAGE_MODEL,
        "prompt": prompt,
        "negative_prompt": negative_prompt
        or "booty, boob, (nsfw), (painting by bad-artist-anime:0.9), (painting by bad-artist:0.9), watermark, text, error, blurry, jpeg artifacts, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, artist name, (worst quality, low quality:1.4), bad anatomy",
        "image_size": "1152x2048",
        "batch_size": 1,
        "seed": 4999999999,
        "num_inference_steps": 20,
        "guidance_scale": 7.5,
    }
    headers = {
        "Authorization": f"Bearer {IMAGE_MODEL_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.post(API_URL, json=payload, headers=headers)
    response.raise_for_status()
    data = response.json()
    image_url = data["images"][0]["url"]

    img_response = requests.get(image_url)
    if img_response.status_code == 200:
        with open(save_path, "wb") as f:
            f.write(img_response.content)
        print(f"Image saved to {save_path}")
        return save_path
    else:
        print("Failed to download image:", img_response.status_code)
        return "Failed to download image"
