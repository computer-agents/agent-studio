from agent.teacher_forcing import TeacherForcingAgent
from desktop_env.computer.env import ComputerEnv


def test_install_extension(
    computer_env: ComputerEnv,
) -> None:
    config_file = f"{config_file_folder}/string_match.json"

    agent = TeacherForcingAgent()
    action_seq = """computer.keyboard.write("The date is 1985/04/18")"""
    agent.set_actions(action_seq)

    # TODO
    # env = computer_env
    # trajectory = tf_roll_out(agent, env, config_file)

    # evalutor = StringEvaluator()
    # score = evalutor(
    #     trajectory, config_file
    # )

    assert score == 1.0
