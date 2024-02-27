# import argparse

# from playground.agent.base_agent import Agent
# from playground.agent.direct_agent import DirectAgent
# from playground.llm.lm_config import construct_llm_config
from playground.llm import setup_model

# def construct_agent(args: argparse.Namespace) -> Agent:
#     llm_config = construct_llm_config(args)

#     agent: Agent
#     if args.agent_type == "direct":
#         agent = DirectAgent(
#             lm_config=llm_config,
#         )
#     else:
#         raise NotImplementedError(f"agent type {args.agent_type} not implemented")
#     return agent


def setup_agent(
    provider: str,
    env: str,
    agent_name: str,
):
    model = setup_model(provider)
    match agent_name:
        case "dummy":
            from playground.agent.base_agent import Agent

            agent = Agent(
                env=env,
                model=model,
                record_path="playground_data/trajectories/dummy",
            )
        case "direct":
            from playground.agent.direct_agent import DirectAgent

            agent = DirectAgent(
                env=env,
                model=model,
                record_path="playground_data/trajectories/direct",
            )
        case _:
            raise ValueError(f"Invalid agent: {agent_name}.")

    return agent
