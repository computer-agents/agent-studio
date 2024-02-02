import pytest

from playground.agent.python import Python


@pytest.fixture(scope="function")
def python_interpreter():
    """Provides the instance of Python for the test."""
    env = Python()
    yield env
    env.close()


def test_python_exec(python_interpreter):
    result = python_interpreter.exec("import sys")
    assert result == {}
    print(python_interpreter.exec("print(sys.version)"))


def test_error_handling(python_interpreter):
    result = python_interpreter.exec('print("Hello, World!")')
    assert result["output"] == ["Hello, World!\n"]
    result = python_interpreter.exec("prvvit()")
    assert result["error"] == "NameError: name 'prvvit' is not defined"


def test_multiple_response(python_interpreter):
    code_with_multiple_prints = (
        'import time\nprint("Hello,")\ntime.sleep(2)\nprint("world!")'
    )
    result = python_interpreter.exec(code_with_multiple_prints)
    assert result["output"] == ["Hello,\n", "world!\n"]


def test_response_data(python_interpreter):
    code_with_plot = """
    import matplotlib.pyplot as plt
    plt.plot([1, 2, 3], [4, 5, 6])
    plt.show()
    """
    result = python_interpreter.exec(code_with_plot)
    assert list(result["output"].keys()) == ["text/plain", "image/png"]
