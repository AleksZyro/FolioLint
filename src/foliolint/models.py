from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

CheckStatus = Literal["ok", "warning", "ignored"]


@dataclass(frozen=True)
class CheckResult:
    category: str
    status: CheckStatus
    message: str
    points: int
    max_points: int
    details: dict[str, Any] = field(default_factory=dict)
    explanation: str = ""
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self, *, include_explanation: bool = False) -> dict[str, Any]:
        data: dict[str, Any] = {
            "category": self.category,
            "status": self.status,
            "message": self.message,
            "points": self.points,
            "max_points": self.max_points,
        }
        if include_explanation:
            data["explanation"] = self.explanation
            data["details"] = self.details
        return data


@dataclass(frozen=True)
class ScanReport:
    path: str
    checks: list[CheckResult]
    recommendations: list[str]
    score: int | None = None
    status: str | None = None
    strict: bool = False

    def to_dict(
        self,
        *,
        include_score: bool = True,
        include_explanation: bool = False,
    ) -> dict[str, Any]:
        data: dict[str, Any] = {
            "checks": [
                check.to_dict(include_explanation=include_explanation) for check in self.checks
            ],
            "recommendations": self.recommendations,
        }
        if include_score:
            data = {"score": self.score, "status": self.status, **data}
        return data

