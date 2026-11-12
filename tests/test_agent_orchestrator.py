
import pytest

from app.agent.orchestrator import AgentOrchestrator
from app.agent.schemas import AgentTask
from app.monitoring.recorder import TraceRecorder
from app.policies.engine import PolicyEngine
from app.policies.enforcer import PolicyEnforcer
from app.policies.schemas import PolicyDecision, ToolPolicy
from app.tools.executor import ToolExecutor
from app.tools.registry import BaseTool, ToolRegistry
from app.tools.schemas import ToolRequest, ToolStatus


class MockGitHubTool(BaseTool):
    """Simulate searching GitHub issues."""

    @property
    def name(self) -> str:
        return "github_search"

    @property
    def description(self) -> str:
        return "Search GitHub issues."

    def execute(self, arguments: dict) -> dict:
        return {
            "issues_found": 3,
            "query": arguments.get("query"),
        }


class FailingTool(BaseTool):
    """Simulate a tool that fails during execution."""

    @property
    def name(self) -> str:
        return "failing_tool"

    @property
    def description(self) -> str:
        return "A tool that always fails."

    def execute(self, arguments: dict) -> dict:
        raise RuntimeError("Simulated tool failure.")


@pytest.fixture
def setup_orchestrator():
    registry = ToolRegistry()
    registry.register(MockGitHubTool())
    registry.register(FailingTool())

    executor = ToolExecutor(registry)

    policy_engine = PolicyEngine()

    policy_engine.register_policy(
        ToolPolicy(
            tool_name="github_search",
            decision=PolicyDecision.ALLOW,
            reason="GitHub searches are permitted.",
        )
    )

    policy_engine.register_policy(
        ToolPolicy(
            tool_name="failing_tool",
            decision=PolicyDecision.ALLOW,
            reason="This tool is permitted for testing.",
        )
    )

    enforcer = PolicyEnforcer(policy_engine, executor)

    recorder = TraceRecorder(enforcer)

    orchestrator = AgentOrchestrator(recorder)

    return orchestrator, recorder


def test_orchestrator_executes_a_tool_successfully(setup_orchestrator):
    orchestrator, recorder = setup_orchestrator

    task = AgentTask(
        objective="Find checkout-related GitHub issues."
    )

    requests = [
        ToolRequest(
            tool_name="github_search",
            arguments={"query": "checkout error"},
        )
    ]

    result = orchestrator.execute(task, requests)

    assert result.status == "completed"
    assert len(result.tool_results) == 1
    assert result.tool_results[0]["result"]["status"] == "success"
    assert len(recorder.get_traces()) == 1


def test_orchestrator_executes_multiple_tools(setup_orchestrator):
    orchestrator, recorder = setup_orchestrator

    task = AgentTask(
        objective="Investigate checkout failures."
    )

    requests = [
        ToolRequest(
            tool_name="github_search",
            arguments={"query": "checkout error"},
        ),
        ToolRequest(
            tool_name="github_search",
            arguments={"query": "payment failure"},
        ),
    ]

    result = orchestrator.execute(task, requests)

    assert result.status == "completed"
    assert len(result.tool_results) == 2
    assert len(recorder.get_traces()) == 2


def test_orchestrator_records_failed_tool_execution(setup_orchestrator):
    orchestrator, recorder = setup_orchestrator

    task = AgentTask(
        objective="Test a failing tool."
    )

    requests = [
        ToolRequest(tool_name="failing_tool")
    ]

    result = orchestrator.execute(task, requests)

    assert result.status == "failed"
    assert result.tool_results[0]["result"]["status"] == "failure"
    assert len(recorder.get_traces()) == 1


def test_orchestrator_handles_approval_required_action(setup_orchestrator):
    orchestrator, recorder = setup_orchestrator

    recorder.executor.executor.policy_engine.register_policy(
        ToolPolicy(
            tool_name="approval_tool",
            decision=PolicyDecision.REQUIRE_APPROVAL,
            reason="Human approval is required.",
        )
    )

    task = AgentTask(
        objective="Perform an action requiring approval."
    )

    # The tool does not need to be registered because the policy
    # enforcer should stop execution before the executor is called.
    requests = [
        ToolRequest(tool_name="approval_tool")
    ]

    result = orchestrator.execute(task, requests)

    assert result.status == "requires_approval"
    assert (
        result.tool_results[0]["result"]["status"]
        == "requires_approval"
    )
    assert len(recorder.get_traces()) == 1


def test_orchestrator_preserves_task_identity(setup_orchestrator):
    orchestrator, _ = setup_orchestrator

    task = AgentTask(
        objective="Find checkout-related GitHub issues."
    )

    result = orchestrator.execute(
        task,
        [
            ToolRequest(tool_name="github_search")
        ],
    )

    assert result.task_id == task.task_id


def test_orchestrator_preserves_execution_identity(setup_orchestrator):
    orchestrator, _ = setup_orchestrator

    task = AgentTask(
        objective="Find checkout-related GitHub issues."
    )

    request = ToolRequest(tool_name="github_search")

    result = orchestrator.execute(task, [request])

    recorded_execution_id = (
        result.tool_results[0]["result"]["execution_id"]
    )

    assert recorded_execution_id == str(request.execution_id)



def test_orchestrator_handles_approval_required_action(setup_orchestrator):
    orchestrator, recorder = setup_orchestrator

    recorder.executor.policy_engine.register_policy(
        ToolPolicy(
            tool_name="approval_tool",
            decision=PolicyDecision.REQUIRE_APPROVAL,
            reason="Human approval is required.",
        )
    )

    task = AgentTask(
        objective="Perform an action requiring approval."
    )

    requests = [
        ToolRequest(tool_name="approval_tool")
    ]

    result = orchestrator.execute(task, requests)

    assert result.status == "requires_approval"
    assert (
        result.tool_results[0]["result"]["status"]
        == "requires_approval"
    )
    assert len(recorder.get_traces()) == 1


def test_orchestrator_handles_empty_tool_request_list(setup_orchestrator):
    orchestrator, recorder = setup_orchestrator

    task = AgentTask(
        objective="Respond without using external tools."
    )

    result = orchestrator.execute(task, [])

    assert result.status == "completed"
    assert result.tool_results == []
    assert recorder.get_traces() == []


def test_orchestrator_stops_after_approval_is_required(
    setup_orchestrator,
):
    orchestrator, recorder = setup_orchestrator

    recorder.executor.policy_engine.register_policy(
        ToolPolicy(
            tool_name="approval_tool",
            decision=PolicyDecision.REQUIRE_APPROVAL,
            reason="Human approval is required.",
        )
    )

    task = AgentTask(
        objective="Request approval before continuing."
    )

    requests = [
        ToolRequest(tool_name="approval_tool"),
        ToolRequest(tool_name="github_search"),
    ]

    result = orchestrator.execute(task, requests)

    assert result.status == "requires_approval"

    # Only the first request should have been executed.
    assert len(result.tool_results) == 1
    assert len(recorder.get_traces()) == 1

    assert (
        result.tool_results[0]["result"]["status"]
        == "requires_approval"
    )
