import pytest
from pydantic import ValidationError

from app.policies.engine import PolicyEngine
from app.policies.schemas import (
    PolicyDecision,
    PolicyEvaluation,
    ToolPolicy,
)
from app.tools.schemas import ToolRequest


def test_register_and_evaluate_allowed_tool():
    engine = PolicyEngine()

    engine.register_policy(
        ToolPolicy(
            tool_name="github_search",
            decision=PolicyDecision.ALLOW,
            reason="Searching GitHub is permitted.",
        )
    )

    request = ToolRequest(tool_name="github_search")
    result = engine.evaluate(request)

    assert result.decision == PolicyDecision.ALLOW
    assert result.tool_name == "github_search"


def test_evaluate_tool_requiring_approval():
    engine = PolicyEngine()

    engine.register_policy(
        ToolPolicy(
            tool_name="linear_create_issue",
            decision=PolicyDecision.REQUIRE_APPROVAL,
            reason="Creating issues requires human approval.",
        )
    )

    request = ToolRequest(tool_name="linear_create_issue")
    result = engine.evaluate(request)

    assert result.decision == PolicyDecision.REQUIRE_APPROVAL


def test_evaluate_denied_tool():
    engine = PolicyEngine()

    engine.register_policy(
        ToolPolicy(
            tool_name="production_delete",
            decision=PolicyDecision.DENY,
            reason="Production deletion is prohibited.",
        )
    )

    request = ToolRequest(tool_name="production_delete")
    result = engine.evaluate(request)

    assert result.decision == PolicyDecision.DENY


def test_unknown_tool_is_denied_by_default():
    engine = PolicyEngine()

    request = ToolRequest(tool_name="unknown_tool")
    result = engine.evaluate(request)

    assert result.decision == PolicyDecision.DENY
    assert "No policy is registered" in result.reason


def test_duplicate_policy_registration_is_rejected():
    engine = PolicyEngine()

    policy = ToolPolicy(
        tool_name="github_search",
        decision=PolicyDecision.ALLOW,
        reason="GitHub searches are permitted.",
    )

    engine.register_policy(policy)

    with pytest.raises(ValueError):
        engine.register_policy(policy)


def test_blank_policy_tool_name_is_rejected():
    with pytest.raises(ValidationError):
        ToolPolicy(
            tool_name="   ",
            decision=PolicyDecision.ALLOW,
            reason="Allowed.",
        )


def test_invalid_policy_decision_is_rejected():
    with pytest.raises(ValidationError):
        ToolPolicy(
            tool_name="github_search",
            decision="maybe",
            reason="Unclear policy.",
        )


def test_policy_evaluation_preserves_reason():
    engine = PolicyEngine()

    engine.register_policy(
        ToolPolicy(
            tool_name="github_search",
            decision=PolicyDecision.ALLOW,
            reason="Read-only searches are permitted.",
        )
    )

    result = engine.evaluate(
        ToolRequest(tool_name="github_search")
    )

    assert result.reason == "Read-only searches are permitted."