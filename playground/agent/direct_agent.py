import logging

from playground.agent.base_agent import Agent
from playground.config import Config
from playground.llm.utils import extract_from_response

config = Config()
logger = logging.getLogger(__name__)


class DirectAgent(Agent):
    """Zero-shot LLM agents."""

    def reset(
        self,
        task_id: str,
        instruction: str,
        record_screen: bool = False,
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
            # Compose model-specific messages from the observation and the trajectory.
            messages_to_model = self.model.compose_messages(
                obs=obs,
                trajectory=self.trajectory,
                system_prompt=self.system_prompt,
            )
            # Generate a response from the model.
            response, info = self.model.generate_response(
                messages=messages_to_model, model=config.model
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
