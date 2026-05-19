from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class CheckResult:
    check_name: str
    column_name: str
    status: str
    severity: str
    metric_value: Any
    threshold: Any
    failed_rows: int
    message: str

    @property
    def is_passed(self) -> bool:
        return self.status.upper() == "PASS"

    def to_record(self) -> dict[str, Any]:
        return {
            "check_name": self.check_name,
            "column_name": self.column_name,
            "status": self.status,
            "severity": self.severity,
            "metric_value": self.metric_value,
            "threshold": self.threshold,
            "failed_rows": self.failed_rows,
            "message": self.message,
        }

