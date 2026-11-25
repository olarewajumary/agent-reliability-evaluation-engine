from app.agent.evidence import EvidenceAggregator
from app.agent.plan_validator import PlanValidator
from app.agent.planner import Planner
from app.agent.response_generator import (
    CitationValidator,
    OllamaResponseGenerator,
)
from app.agent.schemas import (
    AgentExecutionResult,
    AgentTask,
    ExecutionPlan,
)
from app.monitoring.recorder import TraceRecorder
from app.tools.registry import ToolRegistry
from app.tools.schemas import ToolRequest, ToolStatus


class AgentOrchestrator:
    """Coordinate planning, safe execution and evidence-grounded responses."""

    def __init__(
        self,
        recorder: TraceRecorder,
        planner: Planner | None = None,
        registry: ToolRegistry | None = None,
        max_steps: int = 5,
        response_generator: OllamaResponseGenerator | None = None,
    ) -> None:
        self.recorder = recorder
        self.planner = planner
        self.registry = registry
        self.max_steps = max_steps
        self.response_generator = response_generator

        self.evidence_aggregator = EvidenceAggregator()
        self.citation_validator = CitationValidator()

        self.plan_validator = (
            PlanValidator(registry, max_steps)
            if registry is not None
            else None
        )

    @staticmethod
    def _returned_no_results(
        result: dict,
        tool_name: str,
    ) -> bool:
        """Identify explicit empty search results without guessing."""

        if not tool_name.endswith("_search"):
            return False

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

        return False

    def _build_final_answer(
        self,
        task: AgentTask,
        tool_results: list[dict],
        status: str,
    ) -> tuple[list, str | None, list[str], str]:
        """Aggregate evidence and generate a validated answer when possible."""

        evidence = self.evidence_aggregator.aggregate(tool_results)

        if status in {"failed", "requires_approval"}:
            return evidence, None, [], "not_generated"

        if not evidence:
            if status == "no_results":
                answer = (
                    "The search completed successfully, but no matching "
                    "records were found. There is not enough retrieved "
                    "evidence to answer the objective."
                )
            else:
                answer = (
                    "No usable evidence was returned by the executed tools. "
                    "I cannot provide an evidence-grounded answer."
                )

            return evidence, answer, [], "no_evidence"

        if self.response_generator is None:
            return evidence, None, [], "not_configured"

        try:
            generated = self.response_generator.generate(
                objective=task.objective,
                evidence=evidence,
            )

        except Exception:
            # A response-generation failure must not erase successful
            # tool execution or change the underlying execution status.
            return (
                evidence,
                "Evidence was retrieved, but the final response could "
                "not be generated. The retrieved evidence is available "
                "for inspection.",
                [],
                "generation_failed",
            )

        is_valid = self.citation_validator.validate(
            answer=generated,
            evidence=evidence,
        )

        if not is_valid:
            return (
                evidence,
                "Evidence was retrieved, but the generated response "
                "did not contain valid references to the retrieved "
                "evidence. No grounded answer is being presented.",
                [],
                "invalid_citations",
            )

        citations = generated.citations

        citation_text = " ".join(
            f"[{citation}]"
            for citation in citations
        )

        final_answer = f"{generated.answer}\n\nSources: {citation_text}"

        return evidence, final_answer, citations, "generated"

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
                    "tool_name": request.tool_name,
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
                self._returned_no_results(
                    item["result"],
                    item["tool_name"],
                )
                for item in collected_results
            )
        ):
            overall_status = "no_results"

        else:
            overall_status = "completed"

        (
            evidence,
            final_answer,
            cited_evidence_ids,
            response_status,
        ) = self._build_final_answer(
            task=task,
            tool_results=collected_results,
            status=overall_status,
        )

        return AgentExecutionResult(
            task_id=task.task_id,
            status=overall_status,
            tool_results=collected_results,
            plan=plan,
            message=(
                f"Agent task finished with status: {overall_status}."
            ),
            evidence=evidence,
            final_answer=final_answer,
            cited_evidence_ids=cited_evidence_ids,
            response_status=response_status,
        )