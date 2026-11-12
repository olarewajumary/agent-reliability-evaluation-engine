from datetime import datetime, timezone
from time import perf_counter

from app.monitoring.schemas import ExecutionTrace
from app.tools.executor import ToolExecutor
from app.tools.schemas import ToolRequest, ToolResult


class TraceRecorder:
    """Execute tools and record their execution traces."""

    def __init__(self, executor: ToolExecutor) -> None:
        self.executor = executor
        self._traces: list[ExecutionTrace] = []

    def execute(
        self,
        request: ToolRequest,
    ) -> tuple[ToolResult, ExecutionTrace]:

        started_at = datetime.now(timezone.utc)
        start_counter = perf_counter()

        result = self.executor.execute(request)

        finish_counter = perf_counter()
        finished_at = datetime.now(timezone.utc)

        duration_ms = (finish_counter - start_counter) * 1000

        trace = ExecutionTrace(
            execution_id=result.execution_id,
            tool_name=result.tool_name,
            status=result.status,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=duration_ms,
            arguments=request.arguments,
            output=result.output,
            policy_decision=result.policy_decision,
            policy_reason=result.policy_reason,
            error=result.error,
        )

        self._traces.append(trace)

        return result, trace

    def get_traces(self) -> list[ExecutionTrace]:
        return list(self._traces)