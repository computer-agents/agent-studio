import logging
from typing import Any

from playground.desktop_env.eval.connectors.gspace.gdocs import GoogleDocsService
from playground.desktop_env.eval.evaluator import Evaluator

logger = logging.getLogger(__name__)


class GoogleDocsEvaluator(Evaluator):
    name: str = "google_docs"

    def __init__(
        self,
        reference_answer: dict,
        reset_procedure: list[dict],
        eval_tag: str = "",
    ) -> None:
        super().__init__(
            reference_answer=reference_answer,
            reset_procedure=reset_procedure,
            eval_tag=eval_tag,
        )
        self.service = GoogleDocsService()

    def execute(
        self, steps: list[dict[str, dict[str, Any]]], response: str | None = None
    ) -> float:
        score = 1.0
        for step in steps:
            for action, params in step.items():
                match action:
                    case "create_doc":
                        doc = self.service.create_document(title=params["title"])
                        if "content" in params:
                            self.service.append_text(
                                doc["documentId"], params["content"]
                            )
                    case "deduplicate_doc":
                        doc_ids = self.service.search_doc_by_title(params["title"])
                        if len(doc_ids) != 0:
                            self.service.deduplicate_doc(doc_ids, params["content"])
                    case "doc_exact_match":
                        doc_ids = self.service.get_recent_documents()
                        if len(doc_ids) != 0:
                            for doc_id in doc_ids:
                                if self.service.doc_exact_match(
                                    doc_id, params["title"], params["content"]
                                ):
                                    break
                            else:
                                score = 0.0
                    case _:
                        raise Exception(f"Action {action} not supported by Google Docs")

        return score
