
from app.agent.orchestrator import AgentOrchestrator
from app.agent.schemas import AgentExecutionResult, AgentTask
from app.evaluation.scenarios import EvaluationScenario


class ScenarioRunner:
    """Execute evaluation scenarios through the agent orchestrator."""

    def __init__(self, orchestrator: AgentOrchestrator) -> None:
        self.orchestrator = orchestrator

    def run(
        self,
        scenarios: list[EvaluationScenario],
    ) -> dict[str, AgentExecutionResult]:
        """Execute scenarios and return results indexed by case ID."""

        case_ids = [
            scenario.case.case_id
            for scenario in scenarios
        ]

        if len(case_ids) != len(set(case_ids)):
            raise ValueError(
                "Evaluation scenarios contain duplicate case IDs."
            )

        results: dict[str, AgentExecutionResult] = {}

        for scenario in scenarios:
            task = AgentTask(
                objective=scenario.objective,
                context=scenario.context,
            )

            result = self.orchestrator.execute(
                task=task,
                tool_requests=scenario.tool_requests,
            )

            results[scenario.case.case_id] = result

        return results
