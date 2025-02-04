# ComfyUI remote access script
This script is used to send a workflow to a ComfyUI remote instance
and download the resulting images and video without having to save the
images and download them manually. 

This script will download the images/video from the the 'preview' section 
of ComfyUI, you need to use the default ComfyUI preview node:

![alt text](https://github.com/EvanGee/ComfyUI_remote_access/blob/main/assets/image.png?raw=true)
![alt text](https://github.com/EvanGee/ComfyUI_remote_access/blob/main/assets/video.png?raw=true)
```
python3 comfy_client.py --help

usage: comfy_client.py [-h] [--server_address SERVER_ADDRESS] [--media_path MEDIA_PATH] [--type {IMAGE,VIDEO}] [--workflow_path WORKFLOW_PATH] [--frame_rate FRAME_RATE] [--filename_prefix FILENAME_PREFIX]

options:
  -h, --help            show this help message and exit
  --server_address SERVER_ADDRESS
                        Address of the ComfyUI server. Defaults to 127.0.0.1:8188
  --media_path MEDIA_PATH
                        Path to where images/video will be downloaded to. Defaults to current directory.
  --type {IMAGE,VIDEO}  Type of media to download.
  --workflow_path WORKFLOW_PATH
                        Path to the workflow file.
  --frame_rate FRAME_RATE
                        Frame rate of the video. Defaults to 24.
  --filename_prefix FILENAME_PREFIX
                        Prefix for the filenames of the saved images. Defaults to 'output'.
```

### Example: To download images
```
python3 comfy_client.py --type IMAGE --workflow_path workflow_api/image_workflow_api.json
```

### Example: To download video
```
python3 comfy_client.py --type VIDEO --workflow_path workflow_api/video_workflow_api.json
```

I've included some example workflows for video and images. 
## This script hasn't been rigorously tested. Make an issue if anything breaks, I'll fix it ;)  
