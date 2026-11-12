from app.policies.engine import PolicyEngine
from app.policies.schemas import PolicyDecision
from app.tools.executor import ToolExecutor
from app.tools.schemas import ToolRequest, ToolResult, ToolStatus


class PolicyEnforcer:
    """Enforce policy decisions before executing tools."""

    def __init__(
        self,
        policy_engine: PolicyEngine,
        executor: ToolExecutor,
    ) -> None:
        self.policy_engine = policy_engine
        self.executor = executor

    def execute(self, request: ToolRequest) -> ToolResult:
        """Evaluate policy and execute only permitted actions."""

        evaluation = self.policy_engine.evaluate(request)

        # Block actions that are not permitted.
        if evaluation.decision == PolicyDecision.DENY:
            return ToolResult(
                execution_id=request.execution_id,
                tool_name=request.tool_name,
                status=ToolStatus.FAILURE,
                error=f"Policy denied execution: {evaluation.reason}",
            )

        # Pause actions that require human approval.
        if evaluation.decision == PolicyDecision.REQUIRE_APPROVAL:
            return ToolResult(
                execution_id=request.execution_id,
                tool_name=request.tool_name,
                status=ToolStatus.REQUIRES_APPROVAL,
                output={
                    "decision": evaluation.decision.value,
                    "reason": evaluation.reason,
                },
            )

        # Execute only when policy explicitly allows the action.
        return self.executor.execute(request)