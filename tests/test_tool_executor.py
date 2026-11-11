import pytest

from app.tools.executor import ToolExecutor
from app.tools.registry import BaseTool, ToolRegistry
from app.tools.schemas import ToolRequest, ToolStatus


class MockGitHubTool(BaseTool):
    """A simulated GitHub search tool."""

    @property
    def name(self) -> str:
        return "github_search"

    @property
    def description(self) -> str:
        return "Search GitHub issues."

    def execute(self, arguments: dict) -> dict:
        return {
            "issues_found": 2,
            "query": arguments.get("query"),
        }


class FailingTool(BaseTool):
    """A simulated tool that raises an execution error."""

    @property
    def name(self) -> str:
        return "failing_tool"

    @property
    def description(self) -> str:
        return "A tool that always fails."

    def execute(self, arguments: dict) -> dict:
        raise RuntimeError("Simulated API failure.")


class InvalidOutputTool(BaseTool):
    """A simulated tool that violates the output contract."""

    @property
    def name(self) -> str:
        return "invalid_output_tool"

    @property
    def description(self) -> str:
        return "A tool that returns an invalid output."

    def execute(self, arguments: dict) -> dict:
        return "This should have been a dictionary."


def test_executor_returns_successful_result():
    registry = ToolRegistry()
    registry.register(MockGitHubTool())

    executor = ToolExecutor(registry)

    request = ToolRequest(
        tool_name="github_search",
        arguments={"query": "checkout error"},
    )

    result = executor.execute(request)

    assert result.status == ToolStatus.SUCCESS
    assert result.output == {
        "issues_found": 2,
        "query": "checkout error",
    }


def test_executor_preserves_execution_id_and_tool_name():
    registry = ToolRegistry()
    registry.register(MockGitHubTool())

    executor = ToolExecutor(registry)

    request = ToolRequest(tool_name="github_search")

    result = executor.execute(request)

    assert result.execution_id == request.execution_id
    assert result.tool_name == request.tool_name


def test_executor_handles_unknown_tool():
    registry = ToolRegistry()
    executor = ToolExecutor(registry)

    request = ToolRequest(tool_name="unknown_tool")

    result = executor.execute(request)

    assert result.status == ToolStatus.FAILURE
    assert "not registered" in result.error


def test_executor_handles_tool_execution_error():
    registry = ToolRegistry()
    registry.register(FailingTool())

    executor = ToolExecutor(registry)

    request = ToolRequest(tool_name="failing_tool")

    result = executor.execute(request)

    assert result.status == ToolStatus.FAILURE
    assert "Simulated API failure" in result.error


def test_executor_rejects_invalid_tool_output():
    registry = ToolRegistry()
    registry.register(InvalidOutputTool())

    executor = ToolExecutor(registry)

    request = ToolRequest(tool_name="invalid_output_tool")

    result = executor.execute(request)

    assert result.status == ToolStatus.FAILURE
    assert "must be a dictionary" in result.error