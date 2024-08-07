# Install Guide

## Setup Python Environment

Install requirements:

```bash
apt-get install gnome-screenshot xclip xdotool  # If using Ubuntu 22.04
conda create --name agent-studio python=3.11 -y
conda activate agent-studio
pip install -r requirements.txt
pip install -e .
```

## Setup API Keys

All confidential API keys should be stored in `agent_studio/config/api_key.json`, e.g., OpenAI API key, Claude API key, Gemini API key, etc. We have provided an example config in `agent_studio/config/api_key_template.json`.

## Setup Docker (Optional)

We provide a lightweight Dockerfile for reproducing GUI tasks in the online benchmarks or collecting data on a remote machine.

### Build Docker Image

```bash
docker build -f dockerfiles/Dockerfile.ubuntu.amd64 . -t agent-studio:latest
```

### Run Docker

```bash
docker run -d -e RESOLUTION=1024x768 -p 6080:80 -p 5900:5900 -p 8000:8000 -e VNC_PASSWORD=123456 -v /dev/shm:/dev/shm -v ${PWD}/agent_studio/config/:/home/ubuntu/agent_studio/agent_studio/config -v ${PWD}/data:/home/ubuntu/agent_studio/data:ro agent-studio:latest
```

You can browse `http://127.0.0.1:6080` to interact with the remote machine through a browser.
