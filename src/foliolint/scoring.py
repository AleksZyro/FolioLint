from __future__ import annotations

from dataclasses import replace

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
                f"{explanation} Strict mode deducted "
                f"{check.points - new_points} point(s)."
            )
        else:
            explanation = f"Strict mode deducted {check.points - new_points} point(s)."
        strict_checks.append(replace(check, points=new_points, explanation=explanation))
    return strict_checks


def calculate_score(checks: list[CheckResult]) -> int:
    max_points = sum(check.max_points for check in checks if check.max_points > 0)
    if max_points == 0:
        return 0
    points = sum(check.points for check in checks if check.max_points > 0)
    return max(0, min(100, round(points / max_points * 100)))


def _strict_penalty(check: CheckResult) -> int:
    if check.status == "ignored":
        return 0
    if check.category == "README" and check.points < check.max_points:
        return 2
    if check.category == "Tests" and not check.details.get("github_actions"):
        return 3
    if check.category == "Hygiene" and check.status == "warning":
        return 2
    return 0
