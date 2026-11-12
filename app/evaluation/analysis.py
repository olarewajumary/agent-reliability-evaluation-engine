from collections import Counter

from app.evaluation.schemas import (
    BatchEvaluationReport,
    FailureAnalysisReport,
    FailureCategory,
    FailedCaseSummary,
    IssueFrequency,
)


class FailureAnalyzer:
    """Analyze batch evaluation results to identify reliability problems."""

    def analyze(
        self,
        batch_report: BatchEvaluationReport,
    ) -> FailureAnalysisReport:
        """Produce failure breakdowns and identify recurring issues."""

        total_cases = batch_report.total_cases

        categories = []

        for category, count in batch_report.failure_counts.items():
            failure_rate = (
                (count / total_cases) * 100
                if total_cases
                else 0.0
            )

            categories.append(
                FailureCategory(
                    category=category,
                    failed_cases=count,
                    failure_rate=failure_rate,
                )
            )

        categories.sort(
            key=lambda item: item.failed_cases,
            reverse=True,
        )

        failed_cases = [
            FailedCaseSummary(
                case_id=report.case_id,
                score=report.score,
                issues=report.issues,
            )
            for report in batch_report.reports
            if not report.passed
        ]

        issue_counter = Counter(
            issue
            for report in batch_report.reports
            for issue in report.issues
        )

        recurring_issues = [
            IssueFrequency(
                issue=issue,
                occurrences=count,
            )
            for issue, count in issue_counter.most_common()
        ]

        return FailureAnalysisReport(
            total_cases=total_cases,
            passed_cases=batch_report.passed_cases,
            failed_cases=batch_report.failed_cases,
            pass_rate=batch_report.pass_rate,
            failure_categories=categories,
            failed_case_details=failed_cases,
            recurring_issues=recurring_issues,
        )