
import pytest
from pydantic import ValidationError

from app.tools.schemas import ToolRequest, ToolResult, ToolStatus


def test_valid_tool_request():
    request = ToolRequest(
        tool_name="github_search",
        arguments={"query": "checkout error"},
    )

    assert request.tool_name == "github_search"
    assert request.arguments == {"query": "checkout error"}
    assert request.execution_id is not None


def test_each_tool_request_gets_a_unique_execution_id():
    first_request = ToolRequest(tool_name="github_search")
    second_request = ToolRequest(tool_name="linear_create_issue")

    assert first_request.execution_id != second_request.execution_id


def test_unexpected_tool_request_fields_are_rejected():
    with pytest.raises(ValidationError):
        ToolRequest(
            tool_name="github_search",
            admin=True,
        )


def test_tool_request_arguments_are_independent():
    first_request = ToolRequest(tool_name="github_search")
    second_request = ToolRequest(tool_name="linear_create_issue")

    first_request.arguments["query"] = "checkout error"

    assert second_request.arguments == {}


def test_successful_tool_result():
    request = ToolRequest(tool_name="github_search")

    result = ToolResult(
        execution_id=request.execution_id,
        tool_name=request.tool_name,
        status=ToolStatus.SUCCESS,
        output={"issues_found": 3},
    )

    assert result.status == ToolStatus.SUCCESS
    assert result.output["issues_found"] == 3
    assert result.error is None


def test_failed_tool_result():
    request = ToolRequest(tool_name="github_search")

    result = ToolResult(
        execution_id=request.execution_id,
        tool_name=request.tool_name,
        status=ToolStatus.FAILURE,
        error="GitHub API request failed.",
    )

    assert result.status == ToolStatus.FAILURE
    assert result.error == "GitHub API request failed."


def test_invalid_tool_status_is_rejected():
    with pytest.raises(ValidationError):
        ToolResult(
            execution_id=ToolRequest(tool_name="github_search").execution_id,
            tool_name="github_search",
            status="completed",
        )


def test_blank_tool_name_is_rejected():
    with pytest.raises(ValidationError):
        ToolRequest(tool_name="   ")


def test_tool_name_is_normalized():
    request = ToolRequest(tool_name="  github_search  ")

    assert request.tool_name == "github_search"
