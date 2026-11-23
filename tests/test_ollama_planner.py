import json

import pytest

from app.agent.planner import OllamaPlanner, PlanningError
from app.agent.schemas import AgentTask


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_ollama_planner_generates_valid_plan(monkeypatch):

    response_payload = {
        "message": {
            "content": json.dumps({
                "rationale": "Search checkout-related evidence.",
                "actions": [
                    {
                        "tool_name": "slack_search",
                        "arguments": {
                            "query": "checkout",
                        },
                    }
                ],
            })
        }
    }

    def fake_urlopen(request, timeout):
        assert request.full_url.endswith("/api/chat")

        body = json.loads(request.data.decode("utf-8"))

        assert body["model"] == "llama3.2:3b"
        assert body["format"] == "json"
        assert timeout == 360

        return FakeResponse(response_payload)

    monkeypatch.setattr(
        "urllib.request.urlopen",
        fake_urlopen,
    )

    planner = OllamaPlanner()

    task = AgentTask(
        objective="Investigate checkout failures."
    )

    plan = planner.plan(
        task=task,
        available_tools=[
            {
                "name": "slack_search",
                "description": "Search Slack messages.",
                "argument_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                    },
                    "required": ["query"],
                    "additionalProperties": False,
                },
            }
        ],
        max_steps=5,
    )

    assert plan.rationale == "Search checkout-related evidence."
    assert len(plan.actions) == 1
    assert plan.actions[0].tool_name == "slack_search"
    assert plan.actions[0].arguments == {"query": "checkout"}


def test_ollama_planner_rejects_invalid_plan(monkeypatch):

    response_payload = {
        "message": {
            "content": json.dumps({
                "rationale": " ",
                "actions": [],
            })
        }
    }

    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout: FakeResponse(response_payload),
    )

    planner = OllamaPlanner()

    with pytest.raises(PlanningError):
        planner.plan(
            task=AgentTask(
                objective="Investigate checkout failures."
            ),
            available_tools=[],
            max_steps=5,
        )


def test_ollama_planner_rejects_too_many_actions(monkeypatch):

    response_payload = {
        "message": {
            "content": json.dumps({
                "rationale": "Multiple actions.",
                "actions": [
                    {
                        "tool_name": "slack_search",
                        "arguments": {"query": "checkout"},
                    },
                    {
                        "tool_name": "github_search",
                        "arguments": {"query": "checkout"},
                    },
                ],
            })
        }
    }

    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout: FakeResponse(response_payload),
    )

    planner = OllamaPlanner()

    with pytest.raises(PlanningError):
        planner.plan(
            task=AgentTask(
                objective="Investigate checkout failures."
            ),
            available_tools=[],
            max_steps=1,
        )