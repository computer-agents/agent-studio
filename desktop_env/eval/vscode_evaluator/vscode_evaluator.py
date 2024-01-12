from desktop_env.eval.connectors.vscode_connector import VSCodeConnector
from desktop_env.eval.evaluator import Evaluator


class VSCodeEvaluator(Evaluator):
    name: str = "vscode"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.vscode_connector = VSCodeConnector(
            workspace_path=self.env_settings["workspace_path"],
            executable_path=self.env_settings["executable_path"],
        )

    def execute(self, steps):
        for step in steps:
            action: str
            params: dict
            for action, params in step.items():
                match action:
                    case "install_extension":
                        self.vscode_connector.install_extension(params["extension_id"])
                    case "uninstall_extension":
                        self.vscode_connector.uninstall_extension(
                            params["extension_id"]
                        )

    def __call__(self):
        score = 1.0
        try:
            for approach, value in self.reference_answer.items():
                match approach:
                    case "extension_exists":
                        print(self.vscode_connector.list_extensions(versions=True))
                        if (
                            self.vscode_connector.extension_exists(
                                value["extension_id"]
                            )
                            != value["exists"]
                        ):
                            score *= 0.0
        except Exception as e:
            print(f"An error occurred: {e}\nscore may be incorrect")
            score = 0.0

        return score

    def action2str(self, steps: list[dict]) -> list[str]:
        return [""]
