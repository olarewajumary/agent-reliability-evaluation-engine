from datetime import datetime, timezone
from time import perf_counter

from app.monitoring.schemas import ExecutionTrace
from app.tools.executor import ToolExecutor
from app.tools.schemas import ToolRequest, ToolResult


class TraceRecorder:
    """Record the outcome and timing of tool executions."""

    def __init__(self, executor: ToolExecutor) -> None:
        self.executor = executor
        self._traces: list[ExecutionTrace] = []

    def execute(
        self,
        request: ToolRequest,
    ) -> tuple[ToolResult, ExecutionTrace]:
        """Execute a tool and record its execution trace."""

        # Capture the start time.
        started_at = datetime.now(timezone.utc)
        start_counter = perf_counter()

        # Execute the requested tool.
        result = self.executor.execute(request)

        # Capture the finish time.
        finish_counter = perf_counter()
        finished_at = datetime.now(timezone.utc)

        # Calculate elapsed time in milliseconds.
        duration_ms = (finish_counter - start_counter) * 1000

        # Build the execution trace.
        trace = ExecutionTrace(
            execution_id=result.execution_id,
            tool_name=result.tool_name,
            status=result.status,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=duration_ms,
            error=result.error,
        )

        # Keep the trace in memory.
        self._traces.append(trace)

        return result, trace

    def get_traces(self) -> list[ExecutionTrace]:
        """Return all traces recorded so far."""

        return list(self._traces)