
import pytest
from pydantic import ValidationError

from app.agent.schemas import (
    AgentExecutionResult,
    AgentTaskRequest,
    AgentTask,
)


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


def test_valid_agent_execution_result():
    task = AgentTask(
        objective="Investigate checkout failures"
    )

    result = AgentExecutionResult(
        task_id=task.task_id,
        status="completed",
        tool_results=[
            {
                "tool_name": "github_search",
                "issues_found": 3,
            }
        ],
        message="Found three related GitHub issues.",
    )

    assert result.task_id == task.task_id
    assert result.status == "completed"
    assert len(result.tool_results) == 1
    assert result.message == "Found three related GitHub issues."


def test_agent_execution_result_defaults_to_empty_tool_results():
    task = AgentTask(
        objective="Investigate checkout failures"
    )

    result = AgentExecutionResult(
        task_id=task.task_id,
        status="completed",
        message="Task completed without using tools.",
    )

    assert result.tool_results == []


def test_agent_execution_results_have_independent_tool_lists():
    first_task = AgentTask(
        objective="Investigate checkout failures"
    )

    second_task = AgentTask(
        objective="Investigate payment failures"
    )

    first_result = AgentExecutionResult(
        task_id=first_task.task_id,
        status="completed",
        message="First task completed.",
    )

    second_result = AgentExecutionResult(
        task_id=second_task.task_id,
        status="completed",
        message="Second task completed.",
    )

    first_result.tool_results.append(
        {"tool_name": "github_search"}
    )

    assert second_result.tool_results == []


def test_blank_execution_status_is_rejected():
    task = AgentTask(
        objective="Investigate checkout failures"
    )

    with pytest.raises(ValidationError):
        AgentExecutionResult(
            task_id=task.task_id,
            status="   ",
            message="Task completed.",
        )


def test_unexpected_agent_execution_result_fields_are_rejected():
    task = AgentTask(
        objective="Investigate checkout failures"
    )

    with pytest.raises(ValidationError):
        AgentExecutionResult(
            task_id=task.task_id,
            status="completed",
            message="Task completed.",
            admin=True,
        )
