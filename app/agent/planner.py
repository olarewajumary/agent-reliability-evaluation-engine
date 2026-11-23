import json
import logging
import urllib.error
import urllib.request
from typing import Any, Protocol

from openai import OpenAI
from pydantic import ValidationError

from app.agent.schemas import AgentTask, ExecutionPlan, PlannedAction

logger = logging.getLogger(__name__)


class PlanningError(Exception):
    """Raised when an execution plan cannot be generated."""


class Planner(Protocol):
    """Common interface for agent planners."""

    def plan(
        self,
        task: AgentTask,
        available_tools: list[dict[str, Any]],
        max_steps: int,
    ) -> ExecutionPlan:
        ...


class DeterministicPlanner:
    """Generate predictable plans for tests and local development."""

    def plan(
        self,
        task: AgentTask,
        available_tools: list[dict[str, Any]],
        max_steps: int,
    ) -> ExecutionPlan:

        objective = task.objective.casefold()

        available_names = {
            tool["name"]
            for tool in available_tools
        }

        actions: list[PlannedAction] = []

        if any(
            word in objective
            for word in ("create a ticket", "create ticket", "linear ticket")
        ):
            if "create_ticket" not in available_names:
                raise PlanningError(
                    "Ticket creation is not available."
                )

            actions.append(
                PlannedAction(
                    tool_name="create_ticket",
                    arguments={
                        "title": "Investigate reported issue",
                        "description": task.objective,
                    },
                )
            )

        else:
            if "checkout" in objective:
                query = "checkout"
            elif "payment" in objective:
                query = "payment"
            else:
                query = " ".join(task.objective.split()[:3])

            if "slack_search" in available_names:
                actions.append(
                    PlannedAction(
                        tool_name="slack_search",
                        arguments={"query": query},
                    )
                )

            if "github_search" in available_names:
                actions.append(
                    PlannedAction(
                        tool_name="github_search",
                        arguments={"query": query},
                    )
                )

        actions = actions[:max_steps]

        if not actions:
            raise PlanningError(
                "No suitable registered tools were found for this task."
            )

        return ExecutionPlan(
            rationale=(
                "Selected available tools based on the task objective."
            ),
            actions=actions,
        )


class OpenAIPlanner:
    """Generate structured execution plans using an OpenAI model."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
    ) -> None:

        if not api_key.strip():
            raise ValueError("An OpenAI API key is required.")

        self.client = OpenAI(api_key=api_key)
        self.model = model

    def plan(
        self,
        task: AgentTask,
        available_tools: list[dict[str, Any]],
        max_steps: int,
    ) -> ExecutionPlan:

        system_prompt = """
You are an agent planning component.

Your responsibility is to interpret the task and propose a sequence
of tool actions.

You do not execute tools.

You must follow these rules:

1. Use only tools in the supplied tool catalog.
2. Use only arguments defined by each tool's argument schema.
3. Never invent tools or arguments.
4. Do not create tickets unless the user explicitly requests
   ticket creation.
5. Prefer read-only investigation before proposing a write action.
6. Use the minimum number of actions needed.
7. Never exceed the supplied maximum number of actions.
8. If the task cannot be addressed with the available tools,
   return an explanation in the rationale and do not invent
   a substitute capability.

Return a JSON object with exactly this structure:

{
  "rationale": "Brief explanation of the plan",
  "actions": [
    {
      "tool_name": "registered_tool_name",
      "arguments": {}
    }
  ]
}
"""

        user_payload = {
            "objective": task.objective,
            "context": task.context,
            "available_tools": available_tools,
            "maximum_actions": max_steps,
        }

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": json.dumps(user_payload),
                    },
                ],
            )

            content = response.choices[0].message.content

            if not content:
                raise PlanningError(
                    "The planning model returned an empty response."
                )

            return ExecutionPlan.model_validate_json(content)

        except PlanningError:
            raise

        except ValidationError as exc:
            raise PlanningError(
                "The planning model returned an invalid execution plan."
            ) from exc

        except Exception as exc:
            logger.exception(
                "OpenAI planning request failed. Exception type: %s",
                type(exc).__name__,
            )

            raise PlanningError(
                "The planning provider could not generate a plan."
            ) from exc

class OllamaPlanner:
    """Generate execution plans using a locally running Ollama model."""

    def __init__(
        self,
        model: str = "llama3.2:3b",
        base_url: str = "http://localhost:11434",
        timeout: int = 360,
    ) -> None:
        if not model.strip():
            raise ValueError("An Ollama model name is required.")

        if not base_url.strip():
            raise ValueError("An Ollama base URL is required.")

        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def plan(
        self,
        task: AgentTask,
        available_tools: list[dict[str, Any]],
        max_steps: int,
    ) -> ExecutionPlan:

        system_prompt = """
You are an agent planning component.

Generate a plan for the supplied task.

Rules:
1. Only use tools in the supplied tool catalog.
2. Only use arguments defined in each tool's argument schema.
3. Never invent tools or arguments.
4. Never create tickets unless explicitly requested.
5. Prefer read-only investigation before write operations.
6. Use the minimum number of actions necessary.
7. Never exceed the maximum number of actions.
8. If no suitable tool exists, do not invent a substitute.

Return a JSON object with exactly these fields:

{
    "rationale": "Brief explanation",
    "actions": [
        {
            "tool_name": "registered_tool_name",
            "arguments": {}
        }
    ]
}

The actions array must contain at least one valid action.
"""

        user_payload = {
            "objective": task.objective,
            "context": task.context,
            "available_tools": available_tools,
            "maximum_actions": max_steps,
        }

        request_payload = {
            "model": self.model,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0,
            },
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": json.dumps(user_payload),
                },
            ],
        }

        request = urllib.request.Request(
            url=f"{self.base_url}/api/chat",
            data=json.dumps(request_payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout,
            ) as response:
                response_data = json.loads(
                    response.read().decode("utf-8")
                )

            content = response_data.get(
                "message", {}
            ).get("content")

            if not content:
                raise PlanningError(
                    "Ollama returned an empty planning response."
                )

            plan = ExecutionPlan.model_validate_json(content)

            if len(plan.actions) > max_steps:
                raise PlanningError(
                    "Ollama generated more actions than permitted."
                )

            return plan

        except PlanningError:
            raise

        except ValidationError as exc:
            raise PlanningError(
                "Ollama returned an invalid execution plan."
            ) from exc

        except Exception as exc:
            logger.exception(
                "Ollama planning request failed. Exception type: %s",
                type(exc).__name__,
            )

            raise PlanningError(
                "The local planning provider could not generate a plan."
            ) from exc        