import json
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from app.evaluation.schemas import EvaluationCase
from app.evaluation.scenarios import EvaluationScenario


T = TypeVar("T", bound=BaseModel)


def _load_json_list(
    path: str | Path,
    model: type[T],
    dataset_name: str,
) -> list[T]:
    """Load and validate a JSON dataset containing a list of models."""

    dataset_path = Path(path)
    content = dataset_path.read_text(encoding="utf-8")
    raw_items = json.loads(content)

    if not isinstance(raw_items, list):
        raise ValueError(
            f"{dataset_name} must contain a JSON list."
        )

    items = [
        model.model_validate(item)
        for item in raw_items
    ]

    case_ids = [
        item.case_id if isinstance(item, EvaluationCase)
        else item.case.case_id
        for item in items
    ]

    if len(case_ids) != len(set(case_ids)):
        raise ValueError(
            f"{dataset_name} contains duplicate case IDs."
        )

    return items


def load_evaluation_dataset(
    path: str | Path,
) -> list[EvaluationCase]:
    """Load and validate evaluation expectations from JSON."""

    return _load_json_list(
        path=path,
        model=EvaluationCase,
        dataset_name="Evaluation dataset",
    )


def load_evaluation_scenarios(
    path: str | Path,
) -> list[EvaluationScenario]:
    """Load and validate executable evaluation scenarios from JSON."""

    scenarios = _load_json_list(
        path=path,
        model=EvaluationScenario,
        dataset_name="Evaluation scenario dataset",
    )

    if not scenarios:
        raise ValueError(
            "Evaluation scenario dataset must not be empty."
        )

    for scenario in scenarios:
        if not scenario.expected_evidence_ids:
            raise ValueError(
                f"Scenario '{scenario.case.case_id}' "
                "must define at least one expected evidence ID."
            )

    return scenarios