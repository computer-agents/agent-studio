[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3117/)
<a href="https://github.com/psf/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>
<a href="https://mypy-lang.org/"><img src="https://www.mypy-lang.org/static/mypy_badge.svg" alt="Checked with mypy"></a>
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
<a href="https://pre-commit.com/"><img src="https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white" alt="pre-commit"></a>

# Playground

Playground is a holistic and scalable benchmark for measuring and training an AI's general intelligence across the world's supply of games, websites and other applications, in both online desktop and mobile environments. Agents need such a comprehensive and online environment to explore and learn the knowledge of the digital world.

## Setup environment

```bash
apt-get install gnome-screenshot xclip  # If use Ubuntu 22.04
conda create --name playground python=3.11 -y
conda activate playground
pip install -r requirements.txt
pip install -e .
```

(optional, for reproducibility) [Install VirtualBox](https://ubuntu.com/tutorials/how-to-run-ubuntu-desktop-on-a-virtual-machine-using-virtualbox#1-overview) (we use VirtualBox 7 and Ubuntu 22.04 image)

### Google Workspace

[Enable Google APIs, configure OAuth, and download the credentials](https://developers.google.com/docs/api/quickstart/python#set_up_your_environment)

## Contributing

We welcome and value contributions from everyone, no matter the scale. Please check out [CONTRIBUTING.md](./CONTRIBUTING.md) for how to get involved.

## Acknowledgement

- Open Interpreter
- WebArena
- UAC
- vLLM
