import requests
import dotenv
import os
from utils.comfyui import get_image, get_images, get_history
#This is an example that uses the websockets api and the SaveImageWebsocket node to get images directly without
#them being saved to disk

import websocket #NOTE: websocket-client (https://github.com/websocket-client/websocket-client)
import uuid
import json
import urllib.request
import urllib.parse
from PIL import Image
import io
import os

dotenv.load_dotenv()

IMAGE_MODEL = os.getenv("IMAGE_MODEL") or ''
IMAGE_MODEL_KEY = os.getenv("IMAGE_MODEL_KEY") or ''
API_URL = os.getenv("IMAGE_API_BASE") or ''
server_address = os.getenv('COMFYUI_BASE_URL')

def generate_image(prompt="", negative_prompt=None, save_path: str = '.'):
    dir_name = os.path.dirname(save_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    
    if not prompt:
        raise ValueError("Prompt must not be empty.")

    with open('assets/workflow/config.json', 'r', encoding='utf-8') as f:
        prompt_text = f.read()

    prompt = json.loads(prompt_text)
    #set the text prompt for our positive CLIPTextEncode
    prompt["6"]["inputs"]["text"] = prompt

    ws = websocket.WebSocket()
    ws.connect("ws://{}/ws?clientId={}".format(server_address, client_id))
    images = get_images(ws, prompt)
    ws.close() # for in case this example is used in an environment where it will be repeatedly called, like in a Gradio app. otherwise, you'll randomly receive connection timeouts
    # Commented out code to display the output images:

    for node_id in images:
        for idx, image_data in enumerate(images[node_id]):
            image = Image.open(io.BytesIO(image_data))
            image.save(os.path.join(output_dir, save_path))
