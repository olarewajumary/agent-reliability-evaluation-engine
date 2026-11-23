import pytest

from app.agent.orchestrator import AgentOrchestrator
from app.agent.plan_validator import PlanValidator
from app.agent.planner import DeterministicPlanner
from app.agent.schemas import AgentTask, ExecutionPlan, PlannedAction
from app.monitoring.recorder import TraceRecorder
from app.policies.engine import PolicyEngine
from app.policies.enforcer import PolicyEnforcer
from app.policies.schemas import PolicyDecision, ToolPolicy
from app.tools.executor import ToolExecutor
from app.tools.mock_tools import (
    CreateTicketTool,
    GitHubSearchTool,
    SlackSearchTool,
)
from app.tools.registry import ToolRegistry

def build_components():
    registry = ToolRegistry()

    registry.register(SlackSearchTool())
    registry.register(GitHubSearchTool())
    registry.register(CreateTicketTool())

    engine = PolicyEngine()

    engine.register_policy(
        ToolPolicy(
            tool_name="slack_search",
            decision=PolicyDecision.ALLOW,
            reason="Search is permitted.",
        )
    )

    engine.register_policy(
        ToolPolicy(
            tool_name="github_search",
            decision=PolicyDecision.ALLOW,
            reason="Search is permitted.",
        )
    )

    engine.register_policy(
        ToolPolicy(
            tool_name="create_ticket",
            decision=PolicyDecision.REQUIRE_APPROVAL,
            reason="Approval is required.",
        )
    )

    enforcer = PolicyEnforcer(
        policy_engine=engine,
        executor=ToolExecutor(registry),
    )

    recorder = TraceRecorder(enforcer)

    return registry, recorder

def test_deterministic_planner_selects_search_tools():
    registry, _ = build_components()

    planner = DeterministicPlanner()

    task = AgentTask(
        objective="Investigate checkout failures.",
    )

    plan = planner.plan(
        task=task,
        available_tools=registry.describe_tools(),
        max_steps=5,
    )

    assert [
        action.tool_name
        for action in plan.actions
    ] == ["slack_search", "github_search"]

    assert plan.actions[0].arguments == {
        "query": "checkout"
    }

def test_plan_validator_rejects_unknown_tools():
    registry, _ = build_components()

    validator = PlanValidator(
        registry=registry,
        max_steps=5,
    )

    plan = ExecutionPlan(
        rationale="Attempt to use an unavailable tool.",
        actions=[
            PlannedAction(
                tool_name="send_email",
                arguments={},
            )
        ],
    )

    with pytest.raises(ValueError, match="unknown tool"):
        validator.validate(plan)

def test_plan_validator_rejects_invalid_arguments():
    registry, _ = build_components()

    validator = PlanValidator(
        registry=registry,
        max_steps=5,
    )

    plan = ExecutionPlan(
        rationale="Search with an invalid argument.",
        actions=[
            PlannedAction(
                tool_name="slack_search",
                arguments={
                    "query": "checkout",
                    "unexpected": "value",
                },
            )
        ],
    )

    with pytest.raises(ValueError, match="Unexpected arguments"):
        validator.validate(plan)

def test_plan_validator_enforces_maximum_steps():
    registry, _ = build_components()

    validator = PlanValidator(
        registry=registry,
        max_steps=1,
    )

    plan = ExecutionPlan(
        rationale="Too many actions.",
        actions=[
            PlannedAction(
                tool_name="slack_search",
                arguments={"query": "checkout"},
            ),
            PlannedAction(
                tool_name="github_search",
                arguments={"query": "checkout"},
            ),
        ],
    )

    with pytest.raises(ValueError, match="maximum"):
        validator.validate(plan)

def test_planner_execution_preserves_approval_policy():
    registry, recorder = build_components()

    orchestrator = AgentOrchestrator(
        recorder=recorder,
        planner=DeterministicPlanner(),
        registry=registry,
    )

    task = AgentTask(
        objective="Create a ticket about checkout failures.",
    )

    result = orchestrator.execute(task)

    assert result.status == "requires_approval"
    assert result.plan is not None
    assert len(result.tool_results) == 1

    tool_result = result.tool_results[0]["result"]

    assert tool_result["tool_name"] == "create_ticket"
    assert tool_result["status"] == "requires_approval"

    # The simulated ticket must not actually be created.
    assert tool_result["output"]["decision"] == "require_approval"