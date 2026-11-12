import json
from pathlib import Path

from app.evaluation.schemas import EvaluationCase


def load_evaluation_dataset(
    path: str | Path,
) -> list[EvaluationCase]:
    """Load and validate evaluation cases from a JSON file."""

    dataset_path = Path(path)

    content = dataset_path.read_text(encoding="utf-8")
    raw_cases = json.loads(content)

    if not isinstance(raw_cases, list):
        raise ValueError(
            "Evaluation dataset must contain a JSON list."
        )

    cases = [
        EvaluationCase.model_validate(item)
        for item in raw_cases
    ]

    case_ids = [case.case_id for case in cases]

    if len(case_ids) != len(set(case_ids)):
        raise ValueError(
            "Evaluation dataset contains duplicate case IDs."
        )

    return cases