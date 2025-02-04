#This file is used to communicate with ComfyUI. It creates a websocket connection to the server and returns the output images


import websocket #NOTE: websocket-client (https://github.com/websocket-client/websocket-client)
import uuid
import json
import urllib.request
import urllib.parse
from PIL import Image
import io
import cv2
import numpy as np
import os
import shutil as sh
import argparse


class ComfyWebAPI:  
    def __init__(self, server_address: str):
        self.server_address = server_address
        self.client_id = str(uuid.uuid4())

    def queue_prompt(self, workflow: dict):
        """
        Queue a prompt on the ComfyUI server, and return the response
        
        :param workflow: The workflow dictionary
        :return: A dictionary containing the prompt id
        """
        p = {"prompt": workflow, "client_id": self.client_id}
        data = json.dumps(p).encode('utf-8')
        req =  urllib.request.Request("http://{}/prompt".format(self.server_address), data=data)
        return json.loads(urllib.request.urlopen(req).read())

    def get_image(self, filename: str, subfolder: str, folder_type: str):
        """
        Get a single image from the ComfyUI server
        
        :param filename: The filename of the image
        :param subfolder: The subfolder in which the image is stored
        :param folder_type: The type of folder in which the image is stored (e.g. "input", "output")
        :return: The image data in bytes
        """
        data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
        url_values = urllib.parse.urlencode(data)
        with urllib.request.urlopen("http://{}/view?{}".format(self.server_address, url_values)) as response:
            return response.read()

    def get_history(self, prompt_id: str):
        """
        Retrieve the history of a specific prompt from the ComfyUI server.

        :param prompt_id: The unique identifier of the prompt whose history is to be retrieved.
        :return: A dictionary containing the history data of the specified prompt.
        """

        with urllib.request.urlopen("http://{}/history/{}".format(self.server_address, prompt_id)) as response:
            return json.loads(response.read())

    def get_images(self, ws: websocket.WebSocket, workflow:dict):

        """
        Get the images generated by the ComfyUI server after executing a prompt
        
        :param ws: An established websocket connection to the ComfyUI server
        :param workflow: The workflow dictionary
        :return: A dictionary with node ids as keys and lists of image data as values
        """
        prompt_id = self.queue_prompt(workflow)['prompt_id']
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

        # we're grabbing the images from the history
        history = self.get_history(prompt_id)[prompt_id]
        for node_id in history['outputs']:
            node_output = history['outputs'][node_id]
            images_output = []
            if 'images' in node_output:
                for image in node_output['images']:
                    image_data = self.get_image(image['filename'], image['subfolder'], image['type'])
                    images_output.append(image_data)
            output_images[node_id] = images_output

        return output_images
            

    def save_images(self, images:dict,  image_folder:str, filename_prefix:str):
        """
        Save images to the specified folder with a given prefix.

        This function iterates over a dictionary of images, where keys are node IDs 
        and values are lists of image data. Each image is saved in the specified 
        folder with a filename that includes the provided prefix and a unique index.

        :param images: A dictionary with node IDs as keys and lists of image data as values
        :param image_folder: The directory where images will be saved
        :param filename_prefix: The prefix for the filenames of saved images
        """

        i = 0 
        for node_id in images:
            for image_data in images[node_id]:
                image = Image.open(io.BytesIO(image_data))
                image.save(f"{image_folder}/{filename_prefix}_{i}.png")
                i+=1


    def create_video_from_images(self, image_folder: str, video_path="output.mp4", frame_rate=24):
        
        """
        Create a video from the images in the specified folder.

        This function iterates over a directory of images, reads them, and writes them to a video file.
        The video filename is specified by the video_path parameter, and the frame rate is specified by the frame_rate parameter.

        :param image_folder: The directory containing images to be converted to video
        :param video_path: The path to the video file to be written. Defaults to "output.mp4"
        :param frame_rate: The frame rate of the video. Defaults to 24
        """
        images = [img for img in os.listdir(image_folder) if img.endswith(".png")]
        images.sort(key=lambda x: int(x.split('.')[0].split('_')[-1]))
        
        # Read the first image to get the size
        first_image = cv2.imread(os.path.join(image_folder, images[0]))
        height, width, _ = first_image.shape

        # Initialize video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Use 'mp4v' for MP4 format
        video = cv2.VideoWriter(video_path, fourcc, frame_rate, (width, height))

        # Add images to the video
        for image in images:
            img_path = os.path.join(image_folder, image)
            frame = cv2.imread(img_path)
            video.write(frame)

        # Release the video writer
        video.release()
        cv2.destroyAllWindows()

    
    def get_workflow_output(self, workflow_path:str):
        """
        Retrieve the output images generated by the ComfyUI server for a given workflow.

        This function reads a JSON workflow from a file, establishes a websocket 
        connection to the ComfyUI server, sends the workflow as a prompt, and retrieves 
        the generated images.

        :param workflow: The path to the JSON file containing the workflow
        :return: A dictionary with node IDs as keys and lists of image data as values
        """

        workflow = open(workflow_path).read()
        prompt = json.loads(workflow)

        ws = websocket.WebSocket()
        ws.connect(f"ws://{self.server_address}/ws?clientId={self.client_id}")
        image_data = self.get_images(ws, prompt)
        ws.close()

        return image_data

    def download_video(self, workflow_path:str, frame_rate=24, output_dir="videos", filename_prefix="output"):

        """
        Downloads images from the ComfyUI server for a given workflow and creates a video from the downloaded images.

        :param workflow: The path to the workflow file
        :return: None
        """
        image_data = self.get_workflow_output(workflow_path=workflow_path)

        image_folder = "temporary_images_for_video"

        if os.path.exists(image_folder):
            sh.rmtree(image_folder)

        os.mkdir(image_folder)

        self.save_images(images=image_data, image_folder=image_folder, filename_prefix=filename_prefix)
        self.create_video_from_images(image_folder=image_folder, video_path=f"{output_dir}/output.mp4", frame_rate=frame_rate)

        sh.rmtree(image_folder)


    def download_images(self, workflow_path:str, output_dir="images", filename_prefix="output"):
        """
        Downloads images from the ComfyUI server for a given workflow.

        :param workflow_path: The path to the workflow file
        :param output_dir: The directory where images will be saved. Defaults to "images"
        :param filename_prefix: The prefix for the filenames of saved images. Defaults to "output"
        :return: None
        """
        image_data = self.get_workflow_output(workflow_path=workflow_path)
        self.save_images(images=image_data, image_folder=output_dir, filename_prefix=filename_prefix)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('--server_address', type=str, default="127.0.0.1:8188", help="Address of the ComfyUI server. Defaults to 127.0.0.1:8188")
    parser.add_argument('--media_path', type=str, default=".", help="Path to where images/video will be downloaded to. Defaults to current directory.")
    parser.add_argument('--type', type=str, default="IMAGE", choices=["IMAGE", "VIDEO"], help="Type of media to download.")
    parser.add_argument('--workflow_path', type=str, default="workflows/video_workflows_api.json", help="Path to the workflow api file. Needs to be in API format.")
    parser.add_argument('--frame_rate', type=int, default=24, help="Frame rate of the video. Defaults to 24.")
    parser.add_argument('--filename_prefix', type=str, default="output", help="Prefix for the filenames of the saved images. Defaults to 'output'.")

    args = parser.parse_args()
    ComfyWebAPI = ComfyWebAPI(args.server_address)

    if args.type == "IMAGE":
        ComfyWebAPI.download_images(workflow_path=args.workflow_path, output_dir=args.media_path,  filename_prefix=args.filename_prefix)
    elif args.type == "VIDEO":
        ComfyWebAPI.download_video(workflow_path=args.workflow_path, frame_rate=args.frame_rate, output_dir=args.media_path, filename_prefix=args.filename_prefix)

