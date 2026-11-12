from app.policies.engine import PolicyEngine
from app.policies.enforcer import PolicyEnforcer
from app.policies.schemas import PolicyDecision, ToolPolicy
from app.tools.executor import ToolExecutor
from app.tools.registry import BaseTool, ToolRegistry
from app.tools.schemas import ToolRequest, ToolStatus


class MockGitHubTool(BaseTool):
    """A simulated GitHub search tool."""

    def __init__(self) -> None:
        self.execution_count = 0

    @property
    def name(self) -> str:
        return "github_search"

    @property
    def description(self) -> str:
        return "Search GitHub issues."

    def execute(self, arguments: dict) -> dict:
        self.execution_count += 1

        return {
            "issues_found": 2,
            "query": arguments.get("query"),
        }


def create_enforcer(
    decision: PolicyDecision,
) -> tuple[PolicyEnforcer, MockGitHubTool]:
    """Create an enforcer with a configured test tool and policy."""

    registry = ToolRegistry()

    tool = MockGitHubTool()
    registry.register(tool)

    executor = ToolExecutor(registry)

    policy_engine = PolicyEngine()
    policy_engine.register_policy(
        ToolPolicy(
            tool_name="github_search",
            decision=decision,
            reason="Test policy decision.",
        )
    )

    enforcer = PolicyEnforcer(
        policy_engine=policy_engine,
        executor=executor,
    )

    return enforcer, tool


def test_allowed_action_is_executed():
    enforcer, tool = create_enforcer(PolicyDecision.ALLOW)

    request = ToolRequest(
        tool_name="github_search",
        arguments={"query": "checkout error"},
    )

    result = enforcer.execute(request)

    assert result.status == ToolStatus.SUCCESS
    assert result.output["issues_found"] == 2
    assert tool.execution_count == 1


def test_action_requiring_approval_is_not_executed():
    enforcer, tool = create_enforcer(
        PolicyDecision.REQUIRE_APPROVAL
    )

    request = ToolRequest(tool_name="github_search")

    result = enforcer.execute(request)

    assert result.status == ToolStatus.REQUIRES_APPROVAL
    assert tool.execution_count == 0


def test_denied_action_is_not_executed():
    enforcer, tool = create_enforcer(PolicyDecision.DENY)

    request = ToolRequest(tool_name="github_search")

    result = enforcer.execute(request)

    assert result.status == ToolStatus.FAILURE
    assert "Policy denied execution" in result.error
    assert tool.execution_count == 0


def test_unknown_tool_is_denied_without_execution():
    registry = ToolRegistry()
    executor = ToolExecutor(registry)
    policy_engine = PolicyEngine()

    enforcer = PolicyEnforcer(
        policy_engine=policy_engine,
        executor=executor,
    )

    request = ToolRequest(tool_name="unknown_tool")

    result = enforcer.execute(request)

    assert result.status == ToolStatus.FAILURE
    assert "No policy is registered" in result.error


def test_enforcer_preserves_execution_identity():
    enforcer, _ = create_enforcer(PolicyDecision.ALLOW)

    request = ToolRequest(tool_name="github_search")

    result = enforcer.execute(request)

    assert result.execution_id == request.execution_id
    assert result.tool_name == request.tool_name


def test_approval_result_preserves_execution_identity():
    enforcer, _ = create_enforcer(
        PolicyDecision.REQUIRE_APPROVAL
    )

    request = ToolRequest(tool_name="github_search")

    result = enforcer.execute(request)

    assert result.execution_id == request.execution_id
    assert result.tool_name == request.tool_name