Welcome to AgentStudio!
======================================

.. raw:: html
    <h1 align="center">
    AgentStudio
    </h1>

.. raw:: html
    <p align="center">
    <a href="https://ltzheng.github.io/agent-studio/"><b>Documentation</b></a> | <a href="https://arxiv.org/abs/2403."><b>Paper</b></a>
    </p>

.. raw:: html
    <p align="center">
    <a href="https://www.python.org/downloads/release/python-3117/"><img alt="Python 3.11" src="https://img.shields.io/badge/python-3.11-blue.svg"></a>
    <a href="https://github.com/psf/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>
    <a href="https://mypy-lang.org/"><img src="https://www.mypy-lang.org/static/mypy_badge.svg" alt="Checked with mypy"></a>
    <a href="https://www.gnu.org/licenses/agpl-3.0"><img src="https://img.shields.io/badge/License-AGPL%20v3-blue.svg" alt="License: AGPL v3"></a>
    <a href="https://pre-commit.com/"><img src="https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white" alt="pre-commit"></a>
    </p>

AgentStudio is an open toolkit covering the entire lifespan of
building virtual agents that can interact with everything on digital worlds. Here, we open-source the beta of environment implementations, benchmark suite, data collection pipeline, and graphical interfaces to promote research towards generalist virtual agents of the future.

.. image:: ./assets/imgs/overview.png

AgentStudio provides unified observation and action spaces aligned with how humans interact with computers, allowing agent evaluation and data collection on any human-performed task. This feature drastically expands the potential task space. Therefore, AgentStudio can facilitate the development and benchmark of agents that generalize across diverse real-world use cases. In comparison, most previous environments tailored the observation and action spaces solely for specific domains, such as web operations or API calls.

.. image:: ./assets/imgs/agent_space.jpg

Contributing
------------

We plan to expand the collection of environments, tasks, and data over time. Contributions and feedback from everyone on how to make this into a better tool are more than welcome, no matter the scale. Please check out `CONTRIBUTING.md`_ for how to get involved.

.. image:: ./assets/imgs/annotation_example.jpg

.. _`CONTRIBUTING.md`: CONTRIBUTING.md

.. toctree::
   :maxdepth: 4

   getting_started/installation

   getting_started/setup_api_keys

   getting_started/evaluate_agents

   getting_started/start_recording

   getting_started/annotation

   getting_started/troubleshooting
