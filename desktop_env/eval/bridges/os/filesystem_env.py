import os

from desktop_env.eval.bridges.bridge import Bridge


class FilesystemBridge(Bridge):
    def execute(self, steps: list[dict]) -> bool:
        try:
            for step in steps:
                action: str
                params: dict
                for action, params in step.items():
                    match action:
                        case "create_file":
                            file_name = params["path"]
                            if "content" in params:
                                with open(file_name, "w") as f:
                                    f.write(params["content"])
                            else:
                                open(file_name, "w").close()
                        case "mkdir":
                            dir_name = params["path"]
                            os.mkdir(dir_name)
                        case "rm":
                            file_name = params["path"]
                            if os.path.exists(file_name) and os.path.isfile(file_name):
                                os.remove(file_name)
                        case "rmdir":
                            dir_name = params["path"]
                            if os.path.exists(dir_name) and os.path.isdir(dir_name):
                                os.rmdir(dir_name)
                        case "rename":
                            old_name = params["old_name"]
                            new_name = params["new_name"]
                            os.rename(old_name, new_name)
                        case "copy":
                            src = params["src"]
                            dest = params["dest"]
                            os.system(f"cp {src} {dest}")
                        case "move":
                            src = params["src"]
                            dest = params["dest"]
                            os.system(f"mv {src} {dest}")
                        case "chmod":
                            file_name = params["path"]
                            mode: int = int(params["mode"], 8)
                            os.chmod(file_name, mode)
                        case _:
                            raise Exception(f"Action {action} not found")
            return True
        except Exception as e:
            print(f"An error occurred in Filesystem env: {e}")
            return False
