from __future__ import annotations

from dataclasses import replace

from foliolint.check_metadata import (
    HYGIENE,
    METADATA_BY_CATEGORY,
    README,
    TESTS,
)
from foliolint.check_metadata import (
    MEDIA_LIGHT_PROJECT_TYPES as MEDIA_LIGHT_PROJECT_TYPES,
)
from foliolint.models import CheckResult


def score_status(score: int) -> str:
    if score < 50:
        return "Not ready"
    if score < 75:
        return "Needs polish"
    if score < 90:
        return "Almost showcase-ready"
    return "Showcase-ready"


def apply_strict_mode(checks: list[CheckResult]) -> list[CheckResult]:
    strict_checks: list[CheckResult] = []
    for check in checks:
        penalty = _strict_penalty(check)
        if penalty == 0:
            strict_checks.append(check)
            continue

        new_points = max(0, check.points - penalty)
        explanation = check.explanation
        if explanation:
            explanation = (
                f"{explanation} Strict mode deducted {check.points - new_points} point(s)."
            )
        else:
            explanation = f"Strict mode deducted {check.points - new_points} point(s)."
        strict_checks.append(replace(check, points=new_points, explanation=explanation))
    return strict_checks


def apply_project_type(checks: list[CheckResult], project_type: str | None) -> list[CheckResult]:
    if project_type is None:
        return checks

    normalized = project_type.strip().lower()
    adjusted: list[CheckResult] = []
    for check in checks:
        metadata = METADATA_BY_CATEGORY.get(check.category)
        cap = metadata.project_type_max_points.get(normalized) if metadata else None
        if cap is None:
            adjusted.append(check)
            continue

        max_points = min(check.max_points, cap)
        points = min(check.points, max_points)
        details = {**check.details, "project_type_adjustment": normalized}
        explanation = (
            f"{check.explanation} Project type '{normalized}' reduced this category "
            f"to {max_points} max point(s)."
        )
        adjusted.append(
            replace(
                check,
                points=points,
                max_points=max_points,
                details=details,
                explanation=explanation,
            )
        )
    return adjusted


def calculate_score(checks: list[CheckResult]) -> int:
    max_points = sum(check.max_points for check in checks if check.max_points > 0)
    if max_points == 0:
        return 0
    points = sum(check.points for check in checks if check.max_points > 0)
    return max(0, min(100, round(points / max_points * 100)))


def _strict_penalty(check: CheckResult) -> int:
    if check.status == "ignored":
        return 0
    if check.category == README.category and check.points < check.max_points:
        return 2
    if check.category == TESTS.category and not check.details.get("github_actions"):
        return 3
    if check.category == HYGIENE.category and check.status == "warning":
        return 2
    return 0
