
from app.agent.schemas import ExecutionPlan
from app.tools.registry import ToolRegistry


class PlanValidator:
    """Validate plans before any proposed action can execute."""

    def __init__(
        self,
        registry: ToolRegistry,
        max_steps: int = 5,
    ) -> None:

        if max_steps < 1:
            raise ValueError("max_steps must be at least 1.")

        self.registry = registry
        self.max_steps = max_steps

    def validate(self, plan: ExecutionPlan) -> ExecutionPlan:

        if len(plan.actions) > self.max_steps:
            raise ValueError(
                f"Plan exceeds the maximum of {self.max_steps} actions."
            )

        for index, action in enumerate(plan.actions, start=1):

            try:
                tool = self.registry.get(action.tool_name)

            except KeyError as exc:
                raise ValueError(
                    f"Plan action {index} references an unknown tool: "
                    f"'{action.tool_name}'."
                ) from exc

            try:
                tool.validate_arguments(action.arguments)

            except ValueError as exc:
                raise ValueError(
                    f"Invalid arguments in plan action {index}: {exc}"
                ) from exc

        return plan
