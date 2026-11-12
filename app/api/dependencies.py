
from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from app.agent.orchestrator import AgentOrchestrator
from app.evaluation.evaluator import AgentEvaluator
from app.evaluation.runner import EvaluationRunner
from app.evaluation.scenario_runner import ScenarioRunner
from app.evaluation.service import EvaluationService
from app.policies.engine import PolicyEngine
from app.policies.enforcer import PolicyEnforcer
from app.policies.schemas import PolicyDecision, ToolPolicy
from app.monitoring.recorder import TraceRecorder
from app.storage.database import SQLiteDatabase
from app.storage.repository import EvaluationHistoryRepository
from app.tools.executor import ToolExecutor
from app.tools.mock_tools import (
    CreateTicketTool,
    GitHubSearchTool,
    SlackSearchTool,
)
from app.tools.registry import ToolRegistry


@lru_cache
def get_evaluation_repository() -> EvaluationHistoryRepository:
    database = SQLiteDatabase("data/evaluation_history.db")
    return EvaluationHistoryRepository(database)


def get_evaluation_service(
    repository: Annotated[
        EvaluationHistoryRepository,
        Depends(get_evaluation_repository),
    ],
) -> EvaluationService:
    evaluator = AgentEvaluator()
    runner = EvaluationRunner(evaluator=evaluator)

    return EvaluationService(
        runner=runner,
        repository=repository,
    )


def get_scenario_runner() -> ScenarioRunner:
    """Build the simulated agent execution pipeline."""

    registry = ToolRegistry()

    registry.register(SlackSearchTool())
    registry.register(GitHubSearchTool())
    registry.register(CreateTicketTool())

    executor = ToolExecutor(registry)

    policy_engine = PolicyEngine()

    policy_engine.register_policy(
        ToolPolicy(
            tool_name="slack_search",
            decision=PolicyDecision.ALLOW,
            reason="Searching internal messages is permitted.",
        )
    )

    policy_engine.register_policy(
        ToolPolicy(
            tool_name="github_search",
            decision=PolicyDecision.ALLOW,
            reason="Searching repository issues is permitted.",
        )
    )

    policy_engine.register_policy(
        ToolPolicy(
            tool_name="create_ticket",
            decision=PolicyDecision.REQUIRE_APPROVAL,
            reason="Creating a ticket requires human approval.",
        )
    )

    policy_enforcer = PolicyEnforcer(
        policy_engine=policy_engine,
        executor=executor,
    )

    recorder = TraceRecorder(policy_enforcer)

    orchestrator = AgentOrchestrator(recorder)

    return ScenarioRunner(orchestrator)
