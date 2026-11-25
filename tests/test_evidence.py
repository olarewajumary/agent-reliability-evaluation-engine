from app.agent.evidence import EvidenceAggregator


def test_aggregator_extracts_slack_and_github_evidence():
    aggregator = EvidenceAggregator()

    tool_results = [
        {
            "tool_name": "slack_search",
            "result": {
                "status": "success",
                "output": {
                    "count": 1,
                    "messages": [
                        {
                            "message_id": "slack-msg-001",
                            "channel": "engineering",
                            "text": "Checkout fails with a 502 error.",
                        }
                    ],
                },
            },
        },
        {
            "tool_name": "github_search",
            "result": {
                "status": "success",
                "output": {
                    "count": 1,
                    "issues": [
                        {
                            "number": 142,
                            "title": "Checkout API returns 502",
                            "body": "The checkout endpoint returns a 502 response.",
                        }
                    ],
                },
            },
        },
    ]

    evidence = aggregator.aggregate(tool_results)

    assert len(evidence) == 2

    assert evidence[0].evidence_id == "evidence-001"
    assert evidence[0].tool_name == "slack_search"
    assert evidence[0].source_id == "slack-msg-001"
    assert "Checkout fails with a 502 error." in evidence[0].content

    assert evidence[1].evidence_id == "evidence-002"
    assert evidence[1].tool_name == "github_search"
    assert evidence[1].source_id == "142"
    assert "Checkout API returns 502" in evidence[1].content


def test_aggregator_ignores_failed_tool_results():
    aggregator = EvidenceAggregator()

    evidence = aggregator.aggregate(
        [
            {
                "tool_name": "slack_search",
                "result": {
                    "status": "failure",
                    "output": {
                        "messages": [
                            {"message_id": "slack-msg-001", "text": "Example"}
                        ]
                    },
                },
            }
        ]
    )

    assert evidence == []


def test_aggregator_ignores_non_record_outputs():
    aggregator = EvidenceAggregator()

    evidence = aggregator.aggregate(
        [
            {
                "tool_name": "github_search",
                "result": {
                    "status": "success",
                    "output": {
                        "issues_found": 3,
                        "query": "checkout",
                    },
                },
            }
        ]
    )

    assert evidence == []