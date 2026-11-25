import pytest

from app.tools.mock_tools import (
    GitHubSearchTool,
    SlackSearchTool,
    matches_search_query,
    normalize_search_text,
)


def test_normalize_search_text_handles_failure_variations():
    assert normalize_search_text("Checkout FAILS with a 502 error") == {
        "checkout",
        "failure",
    }


def test_failure_variations_match_as_the_same_concept():
    assert matches_search_query(
        "checkout failure",
        "Checkout fails with a 502 error.",
    )


def test_search_matching_ignores_case_and_punctuation():
    assert matches_search_query(
        "CHECKOUT, FAILURE!",
        "Checkout failures reported today.",
    )


def test_search_requires_all_query_concepts():
    assert not matches_search_query(
        "checkout failure",
        "Payment retry creates duplicate requests.",
    )


def test_slack_search_finds_checkout_failure_evidence():
    result = SlackSearchTool().execute({"query": "checkout failure"})

    assert result["count"] == 2
    assert {
        message["message_id"] for message in result["messages"]
    } == {
        "slack-msg-001",
        "slack-msg-002",
    }


def test_github_search_finds_checkout_failure_evidence():
    result = GitHubSearchTool().execute({"query": "checkout failure"})

    assert result["count"] == 2
    assert {
        issue["issue_number"] for issue in result["issues"]
    } == {142, 163}


def test_slack_search_preserves_original_query():
    result = SlackSearchTool().execute({"query": "CHECKOUT FAILURE"})

    assert result["query"] == "CHECKOUT FAILURE"


@pytest.mark.parametrize(
    "tool",
    [SlackSearchTool(), GitHubSearchTool()],
)
@pytest.mark.parametrize(
    "arguments",
    [
        {},
        {"query": ""},
        {"query": "   "},
        {"query": 123},
        {"query": None},
    ],
)
def test_search_tools_reject_invalid_queries(tool, arguments):
    with pytest.raises(ValueError):
        tool.execute(arguments)


def test_search_returns_empty_results_when_no_concepts_match():
    result = SlackSearchTool().execute(
        {"query": "database migration"}
    )

    assert result["count"] == 0
    assert result["messages"] == []