
import pytest

from app.tools.registry import BaseTool, ToolRegistry


class MockGitHubTool(BaseTool):
    """A simulated GitHub search tool for testing."""

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


class MockSlackTool(BaseTool):
    """A simulated Slack search tool for testing."""

    @property
    def name(self) -> str:
        return "slack_search"

    @property
    def description(self) -> str:
        return "Search Slack messages."

    def execute(self, arguments: dict) -> dict:
        return {
            "messages_found": 3,
            "query": arguments.get("query"),
        }


def test_register_tool():
    registry = ToolRegistry()
    tool = MockGitHubTool()

    registry.register(tool)

    assert registry.get("github_search") is tool


def test_duplicate_tool_registration_is_rejected():
    registry = ToolRegistry()

    registry.register(MockGitHubTool())

    with pytest.raises(ValueError):
        registry.register(MockGitHubTool())


def test_retrieve_unknown_tool_is_rejected():
    registry = ToolRegistry()

    with pytest.raises(KeyError):
        registry.get("unknown_tool")


def test_list_registered_tools():
    registry = ToolRegistry()

    registry.register(MockGitHubTool())
    registry.register(MockSlackTool())

    assert registry.list_tools() == [
        "github_search",
        "slack_search",
    ]


def test_registered_tool_can_execute():
    registry = ToolRegistry()
    tool = MockGitHubTool()

    registry.register(tool)

    registered_tool = registry.get("github_search")

    result = registered_tool.execute(
        {"query": "checkout error"}
    )

    assert result == {
        "issues_found": 2,
        "query": "checkout error",
    }


def test_base_tool_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        BaseTool()
