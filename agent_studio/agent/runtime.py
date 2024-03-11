import os
from queue import Empty

import requests
from jupyter_client.manager import KernelManager

from agent_studio.config.config import Config

config = Config()

# Supresses a weird debugging error
os.environ["PYDEVD_DISABLE_FILE_VALIDATION"] = "1"
# turn off colors in "terminal"
os.environ["ANSI_COLORS_DISABLED"] = "1"


class PythonRuntime:
    def __init__(self):
        self.km = KernelManager(kernel_name="python3")
        self.km.start_kernel()
        self.kc = self.km.client()
        self.kc.start_channels()
        self.kc.wait_for_ready()

    def __call__(self, code: str) -> dict:
        self.kc.execute(code)
        result: dict = {}
        # Continuously read messages from the IOPub channel
        try:
            while True:
                msg = self.kc.get_iopub_msg(timeout=config.python_timeout)
                content = msg["content"]
                if (
                    msg["header"]["msg_type"] == "status"
                    and content["execution_state"] == "idle"
                ):
                    # Break the loop when execution is complete
                    break
                if msg["msg_type"] == "stream":
                    if "output" in result:
                        result["output"].append(content["text"])
                    else:
                        result["output"] = [content["text"]]
                elif msg["msg_type"] == "error":
                    errmsg = content["ename"] + ": " + content["evalue"]
                    result["error"] = errmsg
                elif msg["msg_type"] in ["display_data", "execute_result"]:
                    result["output"] = content["data"]
        except Empty as e:
            result["error"] = f"Jupyter timeout: {e}"

        return result

    def close(self) -> None:
        self.kc.stop_channels()
        self.km.shutdown_kernel()
        del self.km
        del self.kc


class RemotePythonRuntime:
    def __call__(self, code: str) -> dict:
        response = requests.post(
            f"http://{config.env_server_addr}:{config.env_server_port}/execute",
            json={"message": code},
        )
        return response.json()

    def close(self) -> None:
        pass
