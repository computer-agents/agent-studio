[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3117/)
<a href="https://github.com/psf/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>
<a href="https://mypy-lang.org/"><img src="https://www.mypy-lang.org/static/mypy_badge.svg" alt="Checked with mypy"></a>
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
<a href="https://pre-commit.com/"><img src="https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white" alt="pre-commit"></a>

# Playground

Playground is a holistic and scalable benchmark for measuring and training an AI's general intelligence across the world's supply of games, websites and other applications, in both online desktop and mobile environments. Agents need such a comprehensive and online environment to explore and learn the knowledge of the digital world.

## Contributing

We welcome and value contributions from everyone, no matter the scale. Please check out [CONTRIBUTING.md](./CONTRIBUTING.md) for how to get involved.

## Setup environment

```bash
apt-get install gnome-screenshot xclip xdotool # If use Ubuntu 22.04
conda create --name playground python=3.11 -y
conda activate playground
pip install -r requirements_{YOUR_SYSTEM_TYPE}.txt
pip install -e .
```

(optional, for reproducibility) [Install VirtualBox](https://ubuntu.com/tutorials/how-to-run-ubuntu-desktop-on-a-virtual-machine-using-virtualbox#1-overview) (we use VirtualBox 7 and Ubuntu 22.04 image)

### Google Workspace

[Enable Google APIs, configure OAuth, download the credentials](https://developers.google.com/docs/api/quickstart/python#set_up_your_environment), and adjust configurations [here](playground/config/config.py).

### Telegram

The telegram evaluator is based on [Pyrogram](https://docs.pyrogram.org/). Obtain the telegram API key by following Telegram’s instructions and rules at https://core.telegram.org/api/obtaining_api_id. After obtaining `api_id` and `api_hash`, modify the `telegram_api_id` and `telegram_api_hash` parameters [here](playground/config/config.py).

## Get Started

### Run on local machine

```bash
python run.py --mode eval
```

### Record agent's trajectory

```bash
python run.py --mode record --env desktop
```

### Run via ssh

If you want to run the agent in a virtual machine or remote machine, setup the `DISPLAY` environment variable via ssh.

Setup `playground/config/config.py`, change `on_ssh` to `True`.

```bash
ssh user@remote # ssh to the remote machine
DISPLAY=YOUR_DISPLAY python run.py --mode eval
```

## Data

The agent trajectories can be found [here](https://huggingface.co/datasets/agentplayground/playground_data)

## Acknowledgement

- [Open Interpreter](https://github.com/KillianLucas/open-interpreter)
- [UAC]()
- [WebArena](https://github.com/web-arena-x/webarena)
- [ScreenAgent](https://github.com/niuzaisheng/ScreenAgent)
