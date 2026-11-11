
import pytest
from pydantic import ValidationError

from app.agent.schemas import AgentTaskRequest, AgentTask


def test_valid_task_request():
    request = AgentTaskRequest(
        objective="Investigate checkout failures"
    )

    assert request.objective == "Investigate checkout failures"
    assert request.context == {}


def test_blank_objective_is_rejected():
    with pytest.raises(ValidationError):
        AgentTaskRequest(objective="   ")


def test_unexpected_fields_are_rejected():
    with pytest.raises(ValidationError):
        AgentTaskRequest(
            objective="Investigate checkout failures",
            admin=True,
        )


def test_each_agent_task_gets_a_unique_id():
    first_task = AgentTask(
        objective="Investigate checkout failures"
    )

    second_task = AgentTask(
        objective="Investigate payment failures"
    )

    assert first_task.task_id != second_task.task_id


def test_task_timestamp_is_timezone_aware():
    task = AgentTask(
        objective="Investigate checkout failures"
    )

    assert task.created_at.tzinfo is not None
    assert task.created_at.utcoffset().total_seconds() == 0
