
from collections import defaultdict
from statistics import mean
from typing import Any

from pydantic import BaseModel, Field


class DiagnosticFinding(BaseModel):
    category: str
    severity: str
    tool_name: str
    message: str
    occurrence_count: int = 1
    case_ids: list[str] = Field(default_factory=list)
    trace_ids: list[str] = Field(default_factory=list)


class ToolDiagnosticSummary(BaseModel):
    tool_name: str
    total_executions: int
    successes: int
    execution_failures: int
    policy_denials: int
    approvals_required: int
    slow_executions: int
    average_duration_ms: float | None
    max_duration_ms: float | None


class RunDiagnosticsReport(BaseModel):
    run_id: str
    total_traces: int
    successful_executions: int
    execution_failures: int
    policy_denials: int
    approvals_required: int
    slow_executions: int
    average_duration_ms: float | None
    slow_threshold_ms: float
    findings: list[DiagnosticFinding]
    tool_summaries: list[ToolDiagnosticSummary]


def _value(value: Any) -> str:
    """Convert an enum or ordinary value into a comparable string."""
    return str(getattr(value, "value", value)).lower()


class AgentReliabilityDiagnostics:
    """
    Analyses persisted execution traces and identifies operational
    reliability problems.

    Policy denials are separated from technical execution failures.
    Approval requests are tracked but are not treated as failures.
    """

    def analyze(
        self,
        run_id: str,
        traces: list,
        slow_threshold_ms: float = 1000.0,
    ) -> RunDiagnosticsReport:

        if slow_threshold_ms <= 0:
            raise ValueError("slow_threshold_ms must be greater than zero")

        findings: list[DiagnosticFinding] = []
        grouped_failures: dict[tuple, list] = defaultdict(list)
        grouped_denials: dict[tuple, list] = defaultdict(list)

        tool_data: dict[str, dict] = defaultdict(
            lambda: {
                "total": 0,
                "successes": 0,
                "failures": 0,
                "denials": 0,
                "approvals": 0,
                "slow": 0,
                "durations": [],
            }
        )

        successful = 0
        failures = 0
        denials = 0
        approvals = 0
        slow_count = 0
        all_durations: list[float] = []

        for trace in traces:
            tool_name = trace.tool_name
            status = _value(trace.status)
            policy_decision = _value(trace.policy_decision or "")
            duration = float(trace.duration_ms)

            tool = tool_data[tool_name]
            tool["total"] += 1
            tool["durations"].append(duration)
            all_durations.append(duration)

            is_denial = policy_decision == "deny"
            is_approval = (
                status == "requires_approval"
                or policy_decision == "require_approval"
            )

            if is_denial:
                denials += 1
                tool["denials"] += 1

                reason = (
                    trace.policy_reason
                    or trace.error
                    or "No denial reason was recorded."
                )

                grouped_denials[(tool_name, reason)].append(trace)

            elif is_approval:
                approvals += 1
                tool["approvals"] += 1

            elif status == "failure":
                failures += 1
                tool["failures"] += 1

                error = trace.error or "No error message was recorded."
                grouped_failures[(tool_name, error)].append(trace)

            elif status == "success":
                successful += 1
                tool["successes"] += 1

            if duration > slow_threshold_ms:
                slow_count += 1
                tool["slow"] += 1

                findings.append(
                    DiagnosticFinding(
                        category="slow_execution",
                        severity="warning",
                        tool_name=tool_name,
                        message=(
                            f"Execution took {duration:.2f} ms, "
                            f"exceeding the {slow_threshold_ms:.2f} ms "
                            "threshold."
                        ),
                        case_ids=[trace.case_id],
                        trace_ids=[trace.trace_id],
                    )
                )

        # Group recurring technical failures so repeated problems
        # are visible instead of producing a long list of duplicates.
        for (tool_name, error), matching_traces in grouped_failures.items():
            findings.append(
                DiagnosticFinding(
                    category="execution_failure",
                    severity="critical",
                    tool_name=tool_name,
                    message=(
                        f"Execution failed: {error}"
                        if len(matching_traces) == 1
                        else (
                            f"The same execution error occurred "
                            f"{len(matching_traces)} times: {error}"
                        )
                    ),
                    occurrence_count=len(matching_traces),
                    case_ids=sorted(
                        {trace.case_id for trace in matching_traces}
                    ),
                    trace_ids=[
                        trace.trace_id for trace in matching_traces
                    ],
                )
            )

        # Policy denials are important safety events, not technical
        # tool failures.
        for (tool_name, reason), matching_traces in grouped_denials.items():
            findings.append(
                DiagnosticFinding(
                    category="policy_denial",
                    severity="warning",
                    tool_name=tool_name,
                    message=f"Policy blocked an action: {reason}",
                    occurrence_count=len(matching_traces),
                    case_ids=sorted(
                        {trace.case_id for trace in matching_traces}
                    ),
                    trace_ids=[
                        trace.trace_id for trace in matching_traces
                    ],
                )
            )

        tool_summaries = []

        for tool_name, data in sorted(tool_data.items()):
            durations = data["durations"]

            tool_summaries.append(
                ToolDiagnosticSummary(
                    tool_name=tool_name,
                    total_executions=data["total"],
                    successes=data["successes"],
                    execution_failures=data["failures"],
                    policy_denials=data["denials"],
                    approvals_required=data["approvals"],
                    slow_executions=data["slow"],
                    average_duration_ms=(
                        round(mean(durations), 2) if durations else None
                    ),
                    max_duration_ms=(
                        round(max(durations), 2) if durations else None
                    ),
                )
            )

        return RunDiagnosticsReport(
            run_id=run_id,
            total_traces=len(traces),
            successful_executions=successful,
            execution_failures=failures,
            policy_denials=denials,
            approvals_required=approvals,
            slow_executions=slow_count,
            average_duration_ms=(
                round(mean(all_durations), 2)
                if all_durations
                else None
            ),
            slow_threshold_ms=slow_threshold_ms,
            findings=findings,
            tool_summaries=tool_summaries,
        )