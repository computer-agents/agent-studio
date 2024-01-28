import logging
from datetime import datetime
from typing import Any

from playground.config import Config
from playground.desktop_env.eval.connectors.vscode_connector import VSCodeConnector
from playground.desktop_env.eval.evaluator import Evaluator

config = Config()
logger = logging.getLogger(__name__)


class VSCodeEvaluator(Evaluator):
    name: str = "vscode"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.vscode_connector = VSCodeConnector(
            workspace_path=config.vscode_workspace_path,
            executable_path=config.vscode_executable_path,
        )

    def execute(
        self, steps: list[dict[str, dict[str, Any]]], response: str | None = None
    ) -> float:
        score = 1.0
        for step in steps:
            for action, params in step.items():
                match action:
                    case "install_extension":
                        self.vscode_connector.install_extension(params["extension_id"])
                    case "uninstall_extension":
                        self.vscode_connector.uninstall_extension(
                            params["extension_id"]
                        )
                    case "uninstall_all_extensions":
                        self.vscode_connector.uninstall_all_extensions()
                    case "extension_installed":
                        score *= self.match_installed_extension(
                            params["extension_id"],
                            exists=params["exists"],
                            version=params.get("version", None),
                            published_before=params.get("published_before", None),
                            published_after=params.get("published_after", None),
                        )
                    case "most_installed_extension":
                        keyword = params["keyword"]
                        extensions = (
                            self.vscode_connector.marketplace_search_by_keyword(keyword)
                        )
                        if len(extensions) == 0:
                            raise Exception(
                                f"Cannot find extension with keyword: {keyword}, \
                                    score may be incorrect"
                            )
                        extension = extensions[0]
                        extension_id = (
                            f"{extension['publisher']['publisherName']}"
                            f".{extension['extensionName']}"
                        )
                        if not self.vscode_connector.extension_installed(extension_id):
                            score = 0.0
                    case _:
                        raise Exception(f"Action {action} not supported by VS Code")

        return score

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
                score *= 0.0
            else:
                installed_version = installed_extensions[extension_id]
                if version is not None and version != installed_version:
                    score *= 0.0
                if published_after is not None or published_before is not None:
                    extensions = (
                        self.vscode_connector.marketplace_search_by_extension_id(
                            extension_id
                        )
                    )
                    if len(extensions) > 1:
                        raise Exception(f"Multiple extension with id: {extension_id}")
                    elif len(extensions) == 0:
                        score *= 0.0
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
                                score *= 0.0
                        if published_before is not None:
                            if last_updated > datetime.fromisoformat(published_before):
                                score *= 0.0
        else:
            if extension_id in installed_extensions:
                score *= 0.0
        return score
