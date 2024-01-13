import os
import shutil


class VSCodeConnector:
    def __init__(
        self,
        workspace_path: str,
        executable_path: str = "code",
    ) -> None:
        self.executable_path = executable_path
        self.workspace_path = workspace_path

    def update_settings(self, settings: str) -> None:
        with open(
            os.path.join(self.workspace_path, ".vscode", "settings.json"), "w"
        ) as f:
            f.write(settings)

    def compare_settings(self, settings: str) -> bool:
        with open(
            os.path.join(self.workspace_path, ".vscode", "settings.json"), "r"
        ) as f:
            current_settings = f.read()
        return current_settings == settings

    def reset_settings(self) -> None:
        shutil.rmtree(os.path.join(self.workspace_path, ".vscode"))

    def list_extensions(self, versions: bool = True) -> list:
        # if extension_list is not None:
        #     if versions:
        #         return [extension.split("@")[0] for extension in extension_list]
        #     else:
        #         return extension_list
        # else:
        extension_list = (
            os.popen(f"{self.executable_path} --list-extensions --show-versions")
            .read()
            .split("\n")
        )
        if versions:
            return [extension.split("@")[0] for extension in extension_list]
        else:
            return extension_list

    def uninstall_all_extensions(self) -> bool:
        # TODO: For safety reasons, disable this method now.
        assert False, "This method is not implemented yet"
        os.system(f"{self.executable_path} --uninstall-extension '*'")
        return self.list_extensions() == []

    def install_extension(self, extension_name: str) -> bool:
        os.system(f"{self.executable_path} --install-extension {extension_name}")
        return extension_name in self.list_extensions(
            versions=True
        ) or extension_name in self.list_extensions(versions=False)

    def uninstall_extension(self, extension_name: str) -> bool:
        os.system(f"{self.executable_path} --uninstall-extension {extension_name}")
        return extension_name not in self.list_extensions(
            versions=True
        ) and extension_name not in self.list_extensions(versions=False)

    def extension_exists(self, extension_name: str) -> bool:
        return extension_name in self.list_extensions(
            versions=True
        ) or extension_name in self.list_extensions(versions=False)
