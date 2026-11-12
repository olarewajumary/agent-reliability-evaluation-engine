
from types import SimpleNamespace

import pytest

from app.monitoring.diagnostics import AgentReliabilityDiagnostics


def make_trace(
    trace_id,
    tool_name="github_search",
    status="success",
    duration_ms=10.0,
    policy_decision=None,
    policy_reason=None,
    error=None,
    case_id="case_001",
):
    return SimpleNamespace(
        trace_id=trace_id,
        case_id=case_id,
        tool_name=tool_name,
        status=status,
        duration_ms=duration_ms,
        policy_decision=policy_decision,
        policy_reason=policy_reason,
        error=error,
    )


def test_diagnostics_separates_failures_denials_and_approvals():
    traces = [
        make_trace("trace_1", status="success"),
        make_trace(
            "trace_2",
            status="failure",
            error="Connection timeout",
            case_id="case_002",
        ),
        make_trace(
            "trace_3",
            status="failure",
            error="Connection timeout",
            case_id="case_003",
        ),
        make_trace(
            "trace_4",
            status="failure",
            policy_decision="deny",
            policy_reason="Permission denied",
            case_id="case_004",
        ),
        make_trace(
            "trace_5",
            status="requires_approval",
            policy_decision="require_approval",
            case_id="case_005",
        ),
        make_trace(
            "trace_6",
            status="success",
            duration_ms=1200.0,
            case_id="case_006",
        ),
    ]

    report = AgentReliabilityDiagnostics().analyze(
        run_id="run_001",
        traces=traces,
        slow_threshold_ms=1000.0,
    )

    assert report.total_traces == 6
    assert report.successful_executions == 2
    assert report.execution_failures == 2
    assert report.policy_denials == 1
    assert report.approvals_required == 1
    assert report.slow_executions == 1

    failure_findings = [
        finding
        for finding in report.findings
        if finding.category == "execution_failure"
    ]

    assert len(failure_findings) == 1
    assert failure_findings[0].occurrence_count == 2
    assert set(failure_findings[0].case_ids) == {
        "case_002",
        "case_003",
    }


def test_policy_denial_is_not_counted_as_execution_failure():
    trace = make_trace(
        "trace_1",
        status="failure",
        policy_decision="deny",
        policy_reason="Action not permitted",
    )

    report = AgentReliabilityDiagnostics().analyze(
        run_id="run_002",
        traces=[trace],
    )

    assert report.policy_denials == 1
    assert report.execution_failures == 0

    assert any(
        finding.category == "policy_denial"
        for finding in report.findings
    )


def test_approval_is_not_counted_as_failure():
    trace = make_trace(
        "trace_1",
        status="requires_approval",
        policy_decision="require_approval",
    )

    report = AgentReliabilityDiagnostics().analyze(
        run_id="run_003",
        traces=[trace],
    )

    assert report.approvals_required == 1
    assert report.execution_failures == 0
    assert report.policy_denials == 0


def test_slow_execution_is_detected():
    trace = make_trace(
        "trace_1",
        duration_ms=750.0,
    )

    report = AgentReliabilityDiagnostics().analyze(
        run_id="run_004",
        traces=[trace],
        slow_threshold_ms=500.0,
    )

    assert report.slow_executions == 1
    assert any(
        finding.category == "slow_execution"
        for finding in report.findings
    )


def test_empty_trace_list_returns_zero_counts():
    report = AgentReliabilityDiagnostics().analyze(
        run_id="run_005",
        traces=[],
    )

    assert report.total_traces == 0
    assert report.successful_executions == 0
    assert report.execution_failures == 0
    assert report.average_duration_ms is None
    assert report.findings == []
    assert report.tool_summaries == []


def test_non_positive_latency_threshold_is_rejected():
    with pytest.raises(ValueError):
        AgentReliabilityDiagnostics().analyze(
            run_id="run_006",
            traces=[],
            slow_threshold_ms=0,
        )