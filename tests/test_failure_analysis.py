import pytest

from app.evaluation.analysis import FailureAnalyzer
from app.evaluation.schemas import (
    BatchEvaluationReport,
    EvaluationReport,
)


@pytest.fixture
def analyzer():
    return FailureAnalyzer()


@pytest.fixture
def batch_report():
    reports = [
        EvaluationReport(
            case_id="case_001",
            tool_selection_correct=True,
            execution_sequence_correct=True,
            task_status_correct=True,
            policy_compliant=True,
            score=100,
            passed=True,
            issues=[],
        ),
        EvaluationReport(
            case_id="case_002",
            tool_selection_correct=False,
            execution_sequence_correct=False,
            task_status_correct=True,
            policy_compliant=True,
            score=50,
            passed=False,
            issues=[
                "The agent selected an unexpected set of tools.",
                "The agent executed tools in an unexpected order.",
            ],
        ),
        EvaluationReport(
            case_id="case_003",
            tool_selection_correct=True,
            execution_sequence_correct=True,
            task_status_correct=False,
            policy_compliant=True,
            score=75,
            passed=False,
            issues=[
                "Expected task status 'completed', "
                "but received 'failed'.",
            ],
        ),
    ]

    return BatchEvaluationReport(
        total_cases=3,
        passed_cases=1,
        failed_cases=2,
        pass_rate=33.3333333333,
        average_score=75,
        failure_counts={
            "tool_selection": 1,
            "execution_sequence": 1,
            "task_status": 1,
            "policy_compliance": 0,
        },
        reports=reports,
    )


def test_analyzer_returns_overall_metrics(
    analyzer,
    batch_report,
):
    analysis = analyzer.analyze(batch_report)

    assert analysis.total_cases == 3
    assert analysis.passed_cases == 1
    assert analysis.failed_cases == 2
    assert analysis.pass_rate == pytest.approx(33.3333333333)


def test_analyzer_identifies_failure_categories(
    analyzer,
    batch_report,
):
    analysis = analyzer.analyze(batch_report)

    categories = {
        item.category: item
        for item in analysis.failure_categories
    }

    assert categories["tool_selection"].failed_cases == 1
    assert categories["execution_sequence"].failed_cases == 1
    assert categories["task_status"].failed_cases == 1
    assert categories["policy_compliance"].failed_cases == 0


def test_analyzer_calculates_failure_rates(
    analyzer,
    batch_report,
):
    analysis = analyzer.analyze(batch_report)

    categories = {
        item.category: item
        for item in analysis.failure_categories
    }

    assert categories["tool_selection"].failure_rate == pytest.approx(
        33.3333333333
    )


def test_analyzer_identifies_failed_cases(
    analyzer,
    batch_report,
):
    analysis = analyzer.analyze(batch_report)

    assert len(analysis.failed_case_details) == 2

    failed_ids = [
        item.case_id
        for item in analysis.failed_case_details
    ]

    assert failed_ids == ["case_002", "case_003"]


def test_analyzer_counts_recurring_issues(
    analyzer,
    batch_report,
):
    analysis = analyzer.analyze(batch_report)

    assert len(analysis.recurring_issues) == 3

    assert analysis.recurring_issues[0].occurrences == 1


def test_analyzer_handles_empty_batch(analyzer):
    empty_report = BatchEvaluationReport(
        total_cases=0,
        passed_cases=0,
        failed_cases=0,
        pass_rate=0,
        average_score=0,
        failure_counts={},
        reports=[],
    )

    analysis = analyzer.analyze(empty_report)

    assert analysis.total_cases == 0
    assert analysis.failure_categories == []
    assert analysis.failed_case_details == []
    assert analysis.recurring_issues == []