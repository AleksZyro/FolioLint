from __future__ import annotations

from pathlib import Path

from foliolint.checks import run_checks
from foliolint.config import load_config
from foliolint.models import ScanReport
from foliolint.scoring import apply_project_type, apply_strict_mode, calculate_score, score_status


def scan_project(path: Path, *, include_score: bool = True, strict: bool = False) -> ScanReport:
    root = path.resolve()
    if not root.exists():
        raise FileNotFoundError(f"Path does not exist: {path}")
    if not root.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {path}")

    config = load_config(root)
    checks = run_checks(root, config)
    checks = apply_project_type(checks, config.project.type)
    if strict:
        checks = apply_strict_mode(checks)

    recommendations = _collect_recommendations(checks)
    score = calculate_score(checks) if include_score else None
    status = score_status(score) if score is not None else None
    return ScanReport(
        path=str(root),
        checks=checks,
        recommendations=recommendations,
        score=score,
        status=status,
        strict=strict,
    )


def _collect_recommendations(checks: list) -> list[str]:
    recommendations: list[str] = []
    seen: set[str] = set()
    for check in checks:
        for recommendation in check.recommendations:
            if recommendation not in seen:
                recommendations.append(recommendation)
                seen.add(recommendation)
    return recommendations[:8]
