
from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from app.evaluation.evaluator import AgentEvaluator
from app.evaluation.runner import EvaluationRunner
from app.evaluation.service import EvaluationService
from app.storage.database import SQLiteDatabase
from app.storage.repository import EvaluationHistoryRepository


@lru_cache
def get_evaluation_repository() -> EvaluationHistoryRepository:
    """Create and cache the persistent evaluation repository."""

    database = SQLiteDatabase(
        "data/evaluation_history.db"
    )

    return EvaluationHistoryRepository(database)


def get_evaluation_service(
    repository: Annotated[
        EvaluationHistoryRepository,
        Depends(get_evaluation_repository),
    ],
) -> EvaluationService:
    """Provide the evaluation service and its dependencies."""

    evaluator = AgentEvaluator()
    runner = EvaluationRunner(evaluator=evaluator)

    return EvaluationService(
        runner=runner,
        repository=repository,
    )
