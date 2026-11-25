import re
from typing import Any

from app.tools.registry import BaseTool


# These terms represent failure indicators in the simulated dataset.
FAILURE_TERMS = {
    "fail",
    "fails",
    "failed",
    "failing",
    "failure",
    "failures",
    "error",
    "errors",
    "502",
}

STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "by",
    "for",
    "from",
    "in",
    "is",
    "of",
    "on",
    "the",
    "to",
    "was",
    "were",
    "with",
}


def normalize_search_text(value: str) -> set[str]:
    """Normalize text into searchable concepts."""
    tokens = re.findall(r"[a-z0-9]+", value.casefold())

    return {
        "failure" if token in FAILURE_TERMS else token
        for token in tokens
        if token not in STOP_WORDS
    }


def matches_search_query(query: str, searchable_text: str) -> bool:
    """Require every normalized query concept to match."""
    query_terms = normalize_search_text(query)
    record_terms = normalize_search_text(searchable_text)

    return bool(query_terms) and query_terms.issubset(record_terms)


class SlackSearchTool(BaseTool):
    """Search a small deterministic collection of simulated Slack messages."""

    name = "slack_search"
    description = "Search simulated Slack messages."

    @property
    def argument_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
            },
            "required": ["query"],
            "additionalProperties": False,
        }

    def __init__(self) -> None:
        self.messages = [
            {
                "message_id": "slack-msg-001",
                "channel": "engineering",
                "text": "Checkout fails with a 502 error after payment confirmation.",
                "author": "developer_01",
            },
            {
                "message_id": "slack-msg-002",
                "channel": "support",
                "text": "Several users reported checkout failures today.",
                "author": "support_01",
            },
            {
                "message_id": "slack-msg-003",
                "channel": "engineering",
                "text": "Payment retry logic may be causing duplicate requests.",
                "author": "developer_02",
            },
        ]

    def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        query = arguments.get("query")

        if not isinstance(query, str) or not query.strip():
            raise ValueError("A non-empty search query is required.")

        matches = [
            message
            for message in self.messages
            if matches_search_query(query, message["text"])
        ]

        return {
            "query": query,
            "count": len(matches),
            "messages": matches,
        }


class GitHubSearchTool(BaseTool):
    """Search a small deterministic collection of simulated GitHub issues."""

    name = "github_search"
    description = "Search simulated GitHub issues."

    @property
    def argument_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
            },
            "required": ["query"],
            "additionalProperties": False,
        }

    def __init__(self) -> None:
        self.issues = [
            {
                "issue_number": 142,
                "title": "Checkout API returns 502 after payment confirmation",
                "body": "The checkout endpoint intermittently returns a 502 response.",
                "state": "open",
            },
            {
                "issue_number": 157,
                "title": "Payment retry creates duplicate requests",
                "body": "Repeated payment attempts may create duplicate requests.",
                "state": "open",
            },
            {
                "issue_number": 163,
                "title": "Improve checkout error logging",
                "body": "Add more diagnostic information to checkout failures.",
                "state": "closed",
            },
        ]

    def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        query = arguments.get("query")

        if not isinstance(query, str) or not query.strip():
            raise ValueError("A non-empty search query is required.")

        matches = [
            issue
            for issue in self.issues
            if matches_search_query(
                query,
                issue["title"] + " " + issue["body"],
            )
        ]

        return {
            "query": query,
            "count": len(matches),
            "issues": matches,
        }


class CreateTicketTool(BaseTool):
    """Simulate creating a Linear ticket."""

    name = "create_ticket"
    description = "Create a ticket in a simulated Linear workspace."

    @property
    def argument_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "description": {"type": "string"},
            },
            "required": ["title", "description"],
            "additionalProperties": False,
        }

    def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        title = arguments.get("title")
        description = arguments.get("description")

        if not isinstance(title, str) or not title.strip():
            raise ValueError("A non-empty ticket title is required.")

        if (
            not isinstance(description, str)
            or not description.strip()
        ):
            raise ValueError("A non-empty ticket description is required.")

        return {
            "ticket_id": "SIM-LIN-001",
            "title": title.strip(),
            "description": description.strip(),
            "status": "created_in_simulation",
        }