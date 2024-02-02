import subprocess


class Shell:
    def exec(self, code: str) -> dict:
        try:
            result = subprocess.run(
                code.split(" "),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            returncode = result.returncode
            if returncode == 0:  # Success
                return {"output": result.stdout}
            else:  # An error occurred during execution
                return {"error": result.stderr, "code": returncode}
        except Exception as e:
            # Handle exceptions raised by subprocess.run
            return {"error": str(e)}
