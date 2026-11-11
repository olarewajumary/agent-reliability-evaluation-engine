from app.monitoring.recorder import TraceRecorder
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
    """A simulated tool that fails during execution."""

    @property
    def name(self) -> str:
        return "failing_tool"

    @property
    def description(self) -> str:
        return "A tool that raises an exception."

    def execute(self, arguments: dict) -> dict:
        raise RuntimeError("Simulated API failure.")


def create_recorder() -> TraceRecorder:
    """Create a recorder with registered test tools."""

    registry = ToolRegistry()
    registry.register(MockGitHubTool())
    registry.register(FailingTool())

    executor = ToolExecutor(registry)

    return TraceRecorder(executor)


def test_recorder_returns_tool_result_and_trace():
    recorder = create_recorder()

    request = ToolRequest(
        tool_name="github_search",
        arguments={"query": "checkout error"},
    )

    result, trace = recorder.execute(request)

    assert result.status == ToolStatus.SUCCESS
    assert trace.status == ToolStatus.SUCCESS


def test_recorder_preserves_execution_identity():
    recorder = create_recorder()

    request = ToolRequest(tool_name="github_search")

    result, trace = recorder.execute(request)

    assert trace.execution_id == request.execution_id
    assert trace.execution_id == result.execution_id
    assert trace.tool_name == request.tool_name


def test_recorder_calculates_execution_duration():
    recorder = create_recorder()

    request = ToolRequest(tool_name="github_search")

    _, trace = recorder.execute(request)

    assert trace.duration_ms >= 0


def test_recorder_captures_timezone_aware_timestamps():
    recorder = create_recorder()

    request = ToolRequest(tool_name="github_search")

    _, trace = recorder.execute(request)

    assert trace.started_at.tzinfo is not None
    assert trace.finished_at.tzinfo is not None


def test_recorder_records_failed_executions():
    recorder = create_recorder()

    request = ToolRequest(tool_name="failing_tool")

    result, trace = recorder.execute(request)

    assert result.status == ToolStatus.FAILURE
    assert trace.status == ToolStatus.FAILURE
    assert "Simulated API failure" in trace.error


def test_recorder_stores_multiple_traces():
    recorder = create_recorder()

    first_request = ToolRequest(tool_name="github_search")
    second_request = ToolRequest(tool_name="failing_tool")

    recorder.execute(first_request)
    recorder.execute(second_request)

    traces = recorder.get_traces()

    assert len(traces) == 2
    assert traces[0].execution_id == first_request.execution_id
    assert traces[1].execution_id == second_request.execution_id


def test_get_traces_does_not_expose_internal_list():
    recorder = create_recorder()

    request = ToolRequest(tool_name="github_search")
    recorder.execute(request)

    traces = recorder.get_traces()
    traces.clear()

    assert len(recorder.get_traces()) == 1