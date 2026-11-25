from typing import Any

from app.agent.schemas import EvidenceItem


class EvidenceAggregator:
    """Normalize records returned by tools into attributable evidence."""

    RECORD_FIELDS = (
        "messages",
        "issues",
        "results",
        "items",
        "documents",
        "records",
    )

    SOURCE_ID_FIELDS = (
        "message_id",
        "issue_number",
        "number",
        "id",
        "ticket_id",
    )

    CONTENT_FIELDS = (
        "title",
        "text",
        "body",
        "description",
        "summary",
        "content",
    )

    def aggregate(
        self,
        tool_results: list[dict[str, Any]],
    ) -> list[EvidenceItem]:
        evidence: list[EvidenceItem] = []

        for tool_result in tool_results:
            tool_name = tool_result.get("tool_name", "unknown_tool")
            result = tool_result.get("result", {})

            if result.get("status") != "success":
                continue

            output = result.get("output")

            if not isinstance(output, dict):
                continue

            for field in self.RECORD_FIELDS:
                records = output.get(field)

                if not isinstance(records, list):
                    continue

                for record in records:
                    if not isinstance(record, dict):
                        continue

                    content = self._extract_content(record)

                    if not content:
                        continue

                    source_id = self._extract_source_id(record)

                    evidence.append(
                        EvidenceItem(
                            evidence_id=f"evidence-{len(evidence) + 1:03d}",
                            tool_name=tool_name,
                            source_id=source_id,
                            content=content,
                            metadata=record,
                        )
                    )

        return evidence

    def _extract_source_id(self, record: dict[str, Any]) -> str | None:
        for field in self.SOURCE_ID_FIELDS:
            value = record.get(field)

            if value is not None:
                return str(value)

        return None

    def _extract_content(self, record: dict[str, Any]) -> str:
        parts: list[str] = []

        for field in self.CONTENT_FIELDS:
            value = record.get(field)

            if isinstance(value, str) and value.strip():
                parts.append(f"{field}: {value.strip()}")

        if parts:
            return "\n".join(parts)

        # Fall back to other readable scalar fields, excluding identifiers.
        excluded = set(self.SOURCE_ID_FIELDS)

        for key, value in record.items():
            if key in excluded:
                continue

            if isinstance(value, (str, int, float, bool)):
                parts.append(f"{key}: {value}")

        return "\n".join(parts)