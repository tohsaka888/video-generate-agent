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
import dotenv
import requests

dotenv.load_dotenv('.env')

server_address = os.getenv('COMFYUI_BASE_URL')
client_id = str(uuid.uuid4())

def queue_prompt(prompt):
    p = {"prompt": prompt, "client_id": client_id}
    data = json.dumps(p).encode('utf-8')
    req =  urllib.request.Request("http://{}/prompt".format(server_address), data=data)
    return json.loads(urllib.request.urlopen(req).read())

def get_image(filename, subfolder, folder_type):
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    url_values = urllib.parse.urlencode(data)
    with urllib.request.urlopen("http://{}/view?{}".format(server_address, url_values)) as response:
        return response.read()

def get_history(prompt_id):
    with urllib.request.urlopen("http://{}/history/{}".format(server_address, prompt_id)) as response:
        return json.loads(response.read())

def get_images(ws, prompt):
    prompt_id = queue_prompt(prompt)['prompt_id']
    output_images = {}
    current_node = ""
    while True:
        out = ws.recv()
        if isinstance(out, str):
            message = json.loads(out)
            if message['type'] == 'executing':
                data = message['data']
                if data['prompt_id'] == prompt_id:
                    if data['node'] is None:
                        break #Execution is done
                    else:
                        current_node = data['node']
        else:
            if current_node == 'save_image_websocket_node':
                images_output = output_images.get(current_node, [])
                images_output.append(out[8:])
                output_images[current_node] = images_output

    return output_images

def generate_image(prompt_text="", negative_prompt=None, save_path: str = '.'):
    dir_name = os.path.dirname(save_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    
    if not prompt_text:
        raise ValueError("Prompt must not be empty.")

    with open('assets/workflow/config.json', 'r', encoding='utf-8') as f:
        workflow_json = f.read()

    workflow = json.loads(workflow_json)
    #set the text prompt for our positive CLIPTextEncode
    workflow["6"]["inputs"]["text"] = prompt_text

    ws = websocket.WebSocket()
    ws.connect("ws://{}/ws?clientId={}".format(server_address, client_id))
    images = get_images(ws, workflow)
    ws.close() # for in case this example is used in an environment where it will be repeatedly called, like in a Gradio app. otherwise, you'll randomly receive connection timeouts
    # Commented out code to display the output images:

    for node_id in images:
        for idx, image_data in enumerate(images[node_id]):
            image = Image.open(io.BytesIO(image_data))
            image.save(save_path)


if __name__ == '__main__':
    generate_image(prompt_text="embedding:lazypos, agirl, long hair, white hair, cute, happy", negative_prompt=None, save_path="output_images/test.png")