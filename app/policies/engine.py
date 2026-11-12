from app.policies.schemas import (
    PolicyDecision,
    PolicyEvaluation,
    ToolPolicy,
)
from app.tools.schemas import ToolRequest


class PolicyEngine:
    """Evaluate whether requested tool actions are permitted."""

    def __init__(self) -> None:
        self._policies: dict[str, ToolPolicy] = {}

    def register_policy(self, policy: ToolPolicy) -> None:
        """Register a policy for a tool."""

        if policy.tool_name in self._policies:
            raise ValueError(
                f"A policy for '{policy.tool_name}' already exists."
            )

        self._policies[policy.tool_name] = policy

    def evaluate(self, request: ToolRequest) -> PolicyEvaluation:
        """Evaluate the policy for a requested tool."""

        policy = self._policies.get(request.tool_name)

        # Unknown tools are denied by default.
        if policy is None:
            return PolicyEvaluation(
                tool_name=request.tool_name,
                decision=PolicyDecision.DENY,
                reason="No policy is registered for this tool.",
            )

        return PolicyEvaluation(
            tool_name=policy.tool_name,
            decision=policy.decision,
            reason=policy.reason,
        )