import os
from queue import Empty

import requests
from jupyter_client.manager import KernelManager

# Supresses a weird debugging error
os.environ["PYDEVD_DISABLE_FILE_VALIDATION"] = "1"
# turn off colors in "terminal"
os.environ["ANSI_COLORS_DISABLED"] = "1"


class PythonRuntime:
    def __init__(self, python_timeout=20):
        self.python_timeout = python_timeout
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
                msg = self.kc.get_iopub_msg(timeout=self.python_timeout)
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

    def close(self) -> bool:
        self.kc.stop_channels()
        self.km.shutdown_kernel()
        del self.km
        del self.kc
        return True

    def reset(self) -> bool:
        if not self.close():
            return False
        self.km = KernelManager(kernel_name="python3")
        self.km.start_kernel()
        self.kc = self.km.client()
        self.kc.start_channels()
        self.kc.wait_for_ready()
        return True


class RemotePythonRuntime:
    def __init__(self, env_server_addr: str, env_server_port: int, python_timeout=20):
        self.env_server_addr = env_server_addr
        self.env_server_port = env_server_port
        self.python_timeout = python_timeout
        response = requests.post(
            f"http://{self.env_server_addr}:{self.env_server_port}/runtime/reset"
        )
        assert response.json()["status"] == "success"

    def __call__(self, code: str) -> dict:
        response = requests.post(
            f"http://{self.env_server_addr}:{self.env_server_port}/execute",
            json={"message": code},
        )
        return response.json()

    def close(self) -> bool:
        return True

    def reset(self) -> bool:
        if not self.close():
            return False
        response = requests.post(
            f"http://{self.env_server_addr}:{self.env_server_port}/runtime/reset"
        )
        if response.json()["status"] == "success":
            return True
        else:
            return False
