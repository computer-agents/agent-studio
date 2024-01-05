[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3117/)
<a href="https://github.com/psf/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>
<a href="https://mypy-lang.org/"><img src="https://www.mypy-lang.org/static/mypy_badge.svg" alt="Checked with mypy"></a>
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

# Playground

Playground is a holistic and scalable benchmark for measuring and training an AI's general intelligence across the world's supply of games, websites and other applications, in both online desktop and mobile environments. Agents need such a comprehensive and online environment to explore and learn the knowledge of the digital world.

## Setup environment

python
```bash
conda create --name playground python=3.11 -y
conda activate playground
pip install -r requirements.txt
```

vscode (ignore if run in vscode)
```
# from https://gist.github.com/jarek-przygodzki/671e9922c8906fbb78194355acd2f449
To add code to PATH in macOS (in order to run code from the command line) we may to open up VS Code and open the 'Command Palette' with Shift+Command+P on Mac, or Shift+Control+P on Linux. In it, enter shell command and look for the Shell Command: Install 'code' command in PATH option.
```



(optional, for reproducibility) [Install VirtualBox](https://ubuntu.com/tutorials/how-to-run-ubuntu-desktop-on-a-virtual-machine-using-virtualbox#1-overview) (we use VirtualBox 7 and Ubuntu 22.04 image)

## Run example

```bash
python minimal_example.py
```

```bash
# eval vscode
python minimal_example.py
```

## Format

```bash
bash scripts/format.sh
```

## Run tests

```bash
cd tests
PYTHONPATH=.. pytest test_computer.py
```

## Acknowledgement

- Open Interpreter
- WebArena
- UAC
- vLLM