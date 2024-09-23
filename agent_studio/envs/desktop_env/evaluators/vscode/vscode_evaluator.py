import json
import logging
import os
import sqlite3
from datetime import datetime

from agent_studio.config import Config
from agent_studio.envs.desktop_env.evaluators.evaluator import (
    Evaluator,
    FeedbackException,
    evaluation_handler,
    reset_handler,
)
from agent_studio.envs.desktop_env.evaluators.vscode.vscode_connector import (
    VSCodeConnector,
)
from agent_studio.utils.human_utils import confirm_action

config = Config()
logger = logging.getLogger(__name__)


class VSCodeEvaluator(Evaluator):
    name: str = "vscode"

    def __init__(self) -> None:
        super().__init__()
        self.vscode_connector = VSCodeConnector(
            workspace_path=config.vscode_workspace_path,
            executable_path=config.vscode_executable_path,
        )

    # for step in steps:
    #     for action, params in step.items():
    #         match action:
    #             case "most_installed_extension":
    #                 keyword = params["keyword"]
    #                 extensions = (
    #                     self.vscode_connector.marketplace_search_by_keyword(keyword)
    #                 )
    #                 if len(extensions) == 0:
    #                     raise Exception(
    #                         f"Cannot find extension with keyword: {keyword}, \
    #                             score may be incorrect"
    #                     )
    #                 extension = extensions[0]
    #                 extension_id = (
    #                     f"{extension['publisher']['publisherName']}"
    #                     f".{extension['extensionName']}"
    #                 )
    #                 if not self.vscode_connector.extension_installed(extension_id):
    #                     score = 0.0
    #             case _:
    #                 raise Exception(f"Action {action} not supported by VS Code")

    @reset_handler("install_extension")
    def install_extension(self, extension_id: str) -> None:
        self.vscode_connector.install_extension(extension_id)

    @reset_handler("uninstall_extension")
    def uninstall_extension(self, extension_id: str) -> None:
        confirm_action(f"Are you sure you want to uninstall {extension_id}?")(
            self.vscode_connector.uninstall_extension
        )(extension_id)

    @reset_handler("uninstall_all_extensions")
    def uninstall_all_extensions(self) -> None:
        confirm_action("Are you sure you want to uninstall all extensions?")(
            self.vscode_connector.uninstall_all_extensions
        )()

    @evaluation_handler("extension_installed")
    def extension_installed(
        self,
        extension_id: str,
        exists: bool,
        version: str | None = None,
        published_before: str | None = None,
        published_after: str | None = None,
    ) -> None:
        self.match_installed_extension(
            extension_id, exists, version, published_before, published_after
        )

    @evaluation_handler("is_extension_disabled")
    def is_extension_disabled(self, extension_list: list[dict]):
        """
        Check if the extension is disabled in VSCode

        Args:
            extension_list (list[dict]): List of extensions to check
                Each extension should have the following structure:
                {
                    "extension_id": str,
                    "enabled": bool,
                }

        Returns:
            bool: True if the extension is disabled, False otherwise
        """
        # Path to VSCode state database (adjust for your OS)
        if os.name == "nt":
            # Windows path
            vscode_state_db = os.path.expanduser(
                r"~/AppData/Roaming/Code/User/globalStorage/state.vscdb"
            )
        elif os.name == "posix":
            # Linux/Mac path
            vscode_state_db = os.path.expanduser(
                "~/.config/Code/User/globalStorage/state.vscdb"
            )
        else:
            raise Exception("Unsupported OS")

        # Check if the file exists
        if not os.path.exists(vscode_state_db):
            raise FeedbackException("VSCode state file not found")

        # Connect to the SQLite database
        conn = sqlite3.connect(vscode_state_db)
        cursor = conn.cursor()

        # Query the extension state
        cursor.execute(
            "SELECT value FROM ItemTable WHERE key = 'extensionsIdentifiers/disabled'"
        )
        result = cursor.fetchone()
        conn.close()
        if result is None:
            extension_states_list = []
        else:
            extension_states_list = json.loads(result[0])
        disabled_extensions = set()
        for extension_state in extension_states_list:
            extension_id = extension_state.get("id", None)
            if extension_id is not None:
                disabled_extensions.add(extension_id)

        for extension_state in extension_list:
            extension_id = extension_state["extension_id"]
            if (extension_id not in disabled_extensions) != extension_state["enabled"]:
                raise FeedbackException(
                    f"Extension {extension_id} state not match,"
                    f" expected {extension_state['enabled']}"
                )

    def match_installed_extension(
        self,
        extension_id: str,
        exists: bool,
        version: str | None = None,
        published_before: str | None = None,
        published_after: str | None = None,
    ) -> float:
        score = 1.0
        installed_extensions: dict = self.vscode_connector.list_extensions()
        if exists:
            if extension_id not in installed_extensions:
                raise FeedbackException(f"Extension {extension_id} is not installed")
            else:
                installed_version = installed_extensions[extension_id]
                if version is not None and version != installed_version:
                    raise FeedbackException(
                        f"Extension {extension_id} is installed with version "
                        f"{installed_version} but expected {version}"
                    )
                if published_after is not None or published_before is not None:
                    extensions = (
                        self.vscode_connector.marketplace_search_by_extension_id(
                            extension_id
                        )
                    )
                    if len(extensions) > 1:
                        raise Exception(f"Multiple extension with id: {extension_id}")
                    elif len(extensions) == 0:
                        raise Exception(
                            f"Cannot find extension with id: {extension_id}"
                        )
                    else:
                        extension = extensions[0]
                        info_find: dict | None = None
                        for extension_version_info in extension["versions"]:
                            extension_version = extension_version_info["version"]
                            if extension_version == installed_version:
                                info_find = extension_version_info
                                break
                        if info_find is None:
                            raise Exception(
                                f"Cannot find extension version: {installed_version}"
                            )
                        last_updated = datetime.fromisoformat(info_find["lastUpdated"])
                        if published_after is not None:
                            if last_updated < datetime.fromisoformat(published_after):
                                raise FeedbackException(
                                    f"Installed extension {extension_id} "
                                    f"is not published after {published_after}"
                                )
                        if published_before is not None:
                            if last_updated > datetime.fromisoformat(published_before):
                                raise FeedbackException(
                                    f"Installed extension {extension_id} "
                                    f"is not published before {published_before}"
                                )
        else:
            if extension_id in installed_extensions:
                raise FeedbackException(
                    f"Extension {extension_id} should not be installed"
                )
        return score
