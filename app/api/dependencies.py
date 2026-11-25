import os
from functools import lru_cache
from typing import Annotated

from dotenv import load_dotenv

from fastapi import Depends, HTTPException

from app.agent.orchestrator import AgentOrchestrator
from app.tools.registry import ToolRegistry
from app.evaluation.evaluator import AgentEvaluator
from app.evaluation.retrieval_evaluator import RetrievalEvaluator
from app.evaluation.runner import EvaluationRunner
from app.evaluation.scenario_runner import ScenarioRunner
from app.evaluation.service import EvaluationService
from app.monitoring.recorder import TraceRecorder
from app.policies.engine import PolicyEngine
from app.policies.enforcer import PolicyEnforcer
from app.policies.schemas import PolicyDecision, ToolPolicy
from app.storage.database import SQLiteDatabase
from app.storage.repository import EvaluationHistoryRepository
from app.tools.executor import ToolExecutor
from app.tools.mock_tools import (
    CreateTicketTool,
    GitHubSearchTool,
    SlackSearchTool,
)
from app.agent.planner import (
    DeterministicPlanner,
    OllamaPlanner,
    OpenAIPlanner,
)

from app.agent.response_generator import OllamaResponseGenerator

load_dotenv()


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


def build_execution_components():
    """Build the shared tool, policy and trace infrastructure."""

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

    enforcer = PolicyEnforcer(
        policy_engine=policy_engine,
        executor=executor,
    )

    recorder = TraceRecorder(enforcer)

    return registry, recorder


def get_scenario_runner() -> ScenarioRunner:
    """Build the deterministic scenario execution pipeline."""

    registry, recorder = build_execution_components()

    orchestrator = AgentOrchestrator(
        recorder=recorder,
        registry=registry,
    )

    return ScenarioRunner(orchestrator)


def get_agent_orchestrator() -> AgentOrchestrator:
    """Build the agent pipeline using the selected planner and responder."""

    provider = os.getenv(
        "PLANNER_PROVIDER",
        "ollama",
    ).strip().lower()

    try:
        max_steps = int(os.getenv("AGENT_MAX_STEPS", "5"))

    except ValueError as exc:
        raise HTTPException(
            status_code=500,
            detail="AGENT_MAX_STEPS must be an integer.",
        ) from exc

    if not 1 <= max_steps <= 10:
        raise HTTPException(
            status_code=500,
            detail="AGENT_MAX_STEPS must be between 1 and 10.",
        )

    response_generator = None

    if provider == "ollama":
        try:
            ollama_timeout = int(
                os.getenv("OLLAMA_TIMEOUT_SECONDS", "360")
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=500,
                detail="OLLAMA_TIMEOUT_SECONDS must be an integer.",
            ) from exc

        if ollama_timeout < 1:
            raise HTTPException(
                status_code=500,
                detail="OLLAMA_TIMEOUT_SECONDS must be greater than zero.",
            )

        ollama_model = os.getenv(
            "OLLAMA_MODEL",
            "llama3.2:3b",
        )

        ollama_base_url = os.getenv(
            "OLLAMA_BASE_URL",
            "http://localhost:11434",
        )

        planner = OllamaPlanner(
            model=ollama_model,
            base_url=ollama_base_url,
            timeout=ollama_timeout,
        )

        response_generator = OllamaResponseGenerator(
            model=ollama_model,
            base_url=ollama_base_url,
            timeout=ollama_timeout,
        )

    elif provider == "deterministic":
        planner = DeterministicPlanner()

    elif provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            raise HTTPException(
                status_code=503,
                detail="Configure OPENAI_API_KEY to use the OpenAI provider.",
            )

        planner = OpenAIPlanner(
            api_key=api_key,
            model=os.getenv(
                "OPENAI_MODEL",
                "gpt-4o-mini",
            ),
        )

    else:
        raise HTTPException(
            status_code=500,
            detail=(
                "Unsupported PLANNER_PROVIDER. "
                "Choose ollama, deterministic, or openai."
            ),
        )

    registry, recorder = build_execution_components()

    return AgentOrchestrator(
        recorder=recorder,
        planner=planner,
        registry=registry,
        max_steps=max_steps,
        response_generator=response_generator,
    )


def get_retrieval_evaluator() -> RetrievalEvaluator:
    return RetrievalEvaluator()