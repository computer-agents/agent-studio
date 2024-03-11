from agent_studio.agent.base_agent import Agent


def test_agent():
    agent = Agent(record_path="data/trajectories/dummy")
    agent.reset(
        env="desktop",
        task_id="dummy",
        instruction="dummy instruction",
        record_screen=True,
    )
    agent.step("import time\ntime.sleep(4)\nprint('Hello, Worlcd!')\nexit()")
    agent.close()
