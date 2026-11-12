from app.policies.engine import PolicyEngine
from app.policies.schemas import PolicyDecision
from app.tools.executor import ToolExecutor
from app.tools.schemas import ToolRequest, ToolResult, ToolStatus


class PolicyEnforcer:
    """Enforce tool policies before allowing execution."""

    def __init__(
        self,
        policy_engine: PolicyEngine,
        executor: ToolExecutor,
    ) -> None:
        self.policy_engine = policy_engine
        self.executor = executor

    def execute(self, request: ToolRequest) -> ToolResult:
        evaluation = self.policy_engine.evaluate(request)

        if evaluation.decision == PolicyDecision.DENY:
            return ToolResult(
                execution_id=request.execution_id,
                tool_name=request.tool_name,
                status=ToolStatus.FAILURE,
                error=f"Policy denied execution: {evaluation.reason}",
                policy_decision=evaluation.decision.value,
                policy_reason=evaluation.reason,
            )

        if evaluation.decision == PolicyDecision.REQUIRE_APPROVAL:
            return ToolResult(
                execution_id=request.execution_id,
                tool_name=request.tool_name,
                status=ToolStatus.REQUIRES_APPROVAL,
                output={
                    "decision": evaluation.decision.value,
                    "reason": evaluation.reason,
                },
                policy_decision=evaluation.decision.value,
                policy_reason=evaluation.reason,
            )

        result = self.executor.execute(request)

        return result.model_copy(
            update={
                "policy_decision": evaluation.decision.value,
                "policy_reason": evaluation.reason,
            }
        )