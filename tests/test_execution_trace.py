from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.monitoring.schemas import ExecutionTrace
from app.tools.schemas import ToolStatus


def test_valid_execution_trace():
    now = datetime.now(timezone.utc)

    trace = ExecutionTrace(
        execution_id=uuid4(),
        tool_name="github_search",
        status=ToolStatus.SUCCESS,
        started_at=now,
        finished_at=now,
        duration_ms=125.5,
    )

    assert trace.tool_name == "github_search"
    assert trace.status == ToolStatus.SUCCESS
    assert trace.duration_ms == 125.5
    assert trace.trace_id is not None


def test_each_trace_gets_a_unique_id():
    now = datetime.now(timezone.utc)

    first_trace = ExecutionTrace(
        execution_id=uuid4(),
        tool_name="github_search",
        status=ToolStatus.SUCCESS,
        started_at=now,
        finished_at=now,
        duration_ms=100,
    )

    second_trace = ExecutionTrace(
        execution_id=uuid4(),
        tool_name="github_search",
        status=ToolStatus.SUCCESS,
        started_at=now,
        finished_at=now,
        duration_ms=100,
    )

    assert first_trace.trace_id != second_trace.trace_id


def test_execution_trace_preserves_execution_id():
    execution_id = uuid4()
    now = datetime.now(timezone.utc)

    trace = ExecutionTrace(
        execution_id=execution_id,
        tool_name="github_search",
        status=ToolStatus.SUCCESS,
        started_at=now,
        finished_at=now,
        duration_ms=100,
    )

    assert trace.execution_id == execution_id


def test_negative_execution_duration_is_rejected():
    now = datetime.now(timezone.utc)

    with pytest.raises(ValidationError):
        ExecutionTrace(
            execution_id=uuid4(),
            tool_name="github_search",
            status=ToolStatus.SUCCESS,
            started_at=now,
            finished_at=now,
            duration_ms=-10,
        )


def test_naive_timestamp_is_rejected():
    with pytest.raises(ValidationError):
        ExecutionTrace(
            execution_id=uuid4(),
            tool_name="github_search",
            status=ToolStatus.SUCCESS,
            started_at=datetime.now(),
            finished_at=datetime.now(timezone.utc),
            duration_ms=100,
        )


def test_blank_tool_name_is_rejected():
    now = datetime.now(timezone.utc)

    with pytest.raises(ValidationError):
        ExecutionTrace(
            execution_id=uuid4(),
            tool_name="   ",
            status=ToolStatus.SUCCESS,
            started_at=now,
            finished_at=now,
            duration_ms=100,
        )


def test_unexpected_fields_are_rejected():
    now = datetime.now(timezone.utc)

    with pytest.raises(ValidationError):
        ExecutionTrace(
            execution_id=uuid4(),
            tool_name="github_search",
            status=ToolStatus.SUCCESS,
            started_at=now,
            finished_at=now,
            duration_ms=100,
            admin=True,
        )