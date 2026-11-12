
from app.agent.schemas import AgentExecutionResult, AgentTask
from app.monitoring.recorder import TraceRecorder
from app.tools.schemas import ToolRequest, ToolStatus


class AgentOrchestrator:
    """Coordinate tool execution for an agent task."""

    def __init__(self, recorder: TraceRecorder) -> None:
        self.recorder = recorder

    def execute(
        self,
        task: AgentTask,
        tool_requests: list[ToolRequest],
    ) -> AgentExecutionResult:
        """Execute a sequence of tool requests for a task."""

        collected_results = []

        for request in tool_requests:
            result, trace = self.recorder.execute(request)

            collected_results.append(
                {
                    "result": result.model_dump(mode="json"),
                    "trace": trace.model_dump(mode="json"),
                }
            )

        # Determine the overall task status.
        statuses = [
            item["result"]["status"]
            for item in collected_results
        ]

        if ToolStatus.REQUIRES_APPROVAL.value in statuses:
            overall_status = "requires_approval"

        elif ToolStatus.FAILURE.value in statuses:
            overall_status = "failed"

        else:
            overall_status = "completed"

        return AgentExecutionResult(
            task_id=task.task_id,
            status=overall_status,
            tool_results=collected_results,
            message=(
                f"Agent task finished with status: {overall_status}."
            ),
        )
