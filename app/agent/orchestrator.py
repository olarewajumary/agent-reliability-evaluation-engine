from app.agent.plan_validator import PlanValidator
from app.agent.planner import Planner
from app.agent.schemas import (
    AgentExecutionResult,
    AgentTask,
    ExecutionPlan,
)
from app.monitoring.recorder import TraceRecorder
from app.tools.registry import ToolRegistry
from app.tools.schemas import ToolRequest, ToolStatus


class AgentOrchestrator:
    """Coordinate planning, validation and safe tool execution."""

    def __init__(
        self,
        recorder: TraceRecorder,
        planner: Planner | None = None,
        registry: ToolRegistry | None = None,
        max_steps: int = 5,
    ) -> None:
        self.recorder = recorder
        self.planner = planner
        self.registry = registry
        self.max_steps = max_steps

        self.plan_validator = (
            PlanValidator(registry, max_steps)
            if registry is not None
            else None
        )

    @staticmethod
    def _returned_no_results(result: dict) -> bool:
        """Identify explicit empty search results without guessing."""

        output = result.get("output")

        if not isinstance(output, dict):
            return False

        count = output.get("count")

        if isinstance(count, int) and not isinstance(count, bool):
            return count == 0

        result_fields = (
            "messages",
            "issues",
            "results",
            "items",
            "documents",
            "records",
        )

        for field in result_fields:
            value = output.get(field)

            if isinstance(value, list):
                return len(value) == 0

        # Unknown output structures are not assumed to be empty.
        return False

    def execute(
        self,
        task: AgentTask,
        tool_requests: list[ToolRequest] | None = None,
    ) -> AgentExecutionResult:
        """Plan when necessary, then execute through policy enforcement."""

        plan: ExecutionPlan | None = None

        if tool_requests is None:
            if (
                self.planner is None
                or self.registry is None
                or self.plan_validator is None
            ):
                raise ValueError(
                    "An agent planner and tool registry are required "
                    "when tool requests are not supplied."
                )

            plan = self.planner.plan(
                task=task,
                available_tools=self.registry.describe_tools(),
                max_steps=self.max_steps,
            )

            plan = self.plan_validator.validate(plan)

            tool_requests = [
                ToolRequest(
                    tool_name=action.tool_name,
                    arguments=action.arguments,
                )
                for action in plan.actions
            ]

        collected_results = []

        for request in tool_requests:
            result, trace = self.recorder.execute(request)

            collected_results.append(
                {
                    "result": result.model_dump(mode="json"),
                    "trace": trace.model_dump(mode="json"),
                }
            )

            if result.status == ToolStatus.REQUIRES_APPROVAL:
                break

            # Stop planner-generated execution after a failure.
            # Explicit scenario requests retain their existing behaviour.
            if (
                plan is not None
                and result.status == ToolStatus.FAILURE
            ):
                break

        statuses = [
            item["result"]["status"]
            for item in collected_results
        ]

        if ToolStatus.REQUIRES_APPROVAL.value in statuses:
            overall_status = "requires_approval"

        elif ToolStatus.FAILURE.value in statuses:
            overall_status = "failed"

        elif (
            collected_results
            and all(
                status == ToolStatus.SUCCESS.value
                for status in statuses
            )
            and all(
                self._returned_no_results(item["result"])
                for item in collected_results
            )
        ):
            overall_status = "no_results"

        else:
            overall_status = "completed"

        return AgentExecutionResult(
            task_id=task.task_id,
            status=overall_status,
            tool_results=collected_results,
            plan=plan,
            message=(
                f"Agent task finished with status: {overall_status}."
            ),
        )