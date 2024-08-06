import logging

from agent_studio.agent.base_agent import BaseAgent
from agent_studio.utils.types import Message, MessageList

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """
You are a world-class programmer who can complete any instruction by executing Python code. Now you are operating a real computer-based environment, and you may be given a screenshot of the current computer screen. The only way to interact with the environment is to write Python code.
You are given a task instruction in the form of a string and you need to write Python code to complete it.
You are using Jupyter Notebook to execute the code and shell commands, so generate code/shell commands step by step with multiple blocks. You can use jupyter internal operator "%" and "!". The generated code/shell commands should be wrapped between "```python\n" and "\n```". Your response should include and only include one code block. You will get the execution result of the code.
You can interact with the Notebook multiple rounds. Thus, if you are not sure about the code, you can submit the code to see the result and modify the code if needed. When you think the instruction is completed and the code is correct, end the code block with `exit()`.
For simplicity, you can use the following code snippets:
0. You are probably given a screenshot of the current computer screen. You can only use the Jupyter Notebook to interact with the environment. We have provided the initial code to access the mouse and keyboard:
```python
from agent_studio.envs.desktop_env import Mouse, Keyboard
mouse = Mouse()
keyboard = Keyboard()
```
You can use the `mouse` and `keyboard` objects to interact with the environment. `mouse.click(x: int, y: int, button: str, clicks: int, interval: float)` can be used to click the "button" at the specified position "click" times with a specific interval. You can choose "button" from "left", "right", and middle". `keyboard.type(text: str, interval: float)` can be used to type the specified text with a specific interval. `keyboard.hotkey(keys: list[str])` can be used to press hotkeys.
"""  # noqa: E501


class DirectAgent(BaseAgent):
    """Zero-shot agents."""

    name: str = "direct"

    @property
    def action_prompt(self) -> MessageList:
        messages: MessageList = []
        messages.append(Message(role="system", content=SYSTEM_PROMPT))
        messages.append(
            Message(role="user", content=f"The task instruction: {self.instruction}")
        )
        for step in self.trajectory:
            messages.append(
                Message(
                    role="assistant", content=f"Action:\n```python\n{step.action}\n```"
                )
            )

        if self.step_info.obs is not None:
            messages.append(Message(role="user", content=self.step_info.obs))

        return messages
