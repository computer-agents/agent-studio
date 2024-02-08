import logging
from typing import Any

from playground.agent.base_agent import Agent
from playground.config import Config
from playground.llm.utils import encode_image, extract_from_response

config = Config()
logger = logging.getLogger(__name__)


class DirectAgent(Agent):
    """Zero-shot LLM agents."""

    def reset(
        self,
        task_id: str,
        instruction: str,
        record_screen: bool = False,
        **kwargs,
    ) -> None:
        super().reset(
            task_id=task_id, instruction=instruction, record_screen=record_screen
        )
        with open(config.system_prompt_path, "r") as f:
            self.system_prompt = f.read()

    def run(self) -> list:
        # Initialize the interface the agent needs.
        match self.env:
            case "desktop":
                init_code = (
                    "from playground.env.desktop_env import Shell, Keyboard, Mouse\n\n"
                    "shell = Shell()\nkeyboard = Keyboard()\nmouse = Mouse()\n"
                )
                self.step(init_code)
            case _:
                raise ValueError(f"Invalid env: {self.env}.")

        # Loop until the task is done or the max step is reached.
        for _ in range(config.max_step):
            # Get the observation from the environment.
            obs = self.get_obs()

            # Get the response from the LLM and parse the code.
            messages: list[dict[str, Any]] = []
            messages.append({"role": "system", "content": self.system_prompt})
            for step in self.trajectory:
                messages.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": encode_image(step["obs"])},
                            }
                        ],
                    }
                )
                messages.append({"role": "assistant", "content": step["act"]})
            messages.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": encode_image(obs)},
                        }
                    ],
                }
            )
            response = self.model.generate_response(
                messages=messages, model=config.model
            )
            raw_code = extract_from_response(response)

            # Execute the code and record the result.
            self.recorder.add_event(raw_code)
            done = raw_code.endswith(config.stop_code)
            if done:
                code = raw_code[: -len(config.stop_code)]
            else:
                code = raw_code
            result = self.step(code)
            self.trajectory.append(
                {"obs": obs, "act": raw_code, "res": result, "done": done}
            )
            if done:
                break

        if self.record_screen:
            self.recorder.stop()
        self.recorder.save()

        return self.trajectory
