from __future__ import annotations

from pathlib import Path

from foliolint.check_metadata import METADATA
from foliolint.checks import detect_project_type, run_checks
from foliolint.config import load_config
from foliolint.models import CheckResult, ScanReport
from foliolint.scoring import apply_project_type, apply_strict_mode, calculate_score, score_status


def scan_project(path: Path, *, include_score: bool = True, strict: bool = False) -> ScanReport:
    root = path.resolve()
    if not root.exists():
        raise FileNotFoundError(f"Path does not exist: {path}")
    if not root.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {path}")

    config = load_config(root)
    checks = run_checks(root, config)
    project_type = config.project.type
    if not project_type:
        metadata = next((check for check in checks if check.category == METADATA.category), None)
        if metadata is not None and "project_type" in metadata.details:
            project_type = metadata.details["project_type"]
        else:
            project_type, _ = detect_project_type(root)
    checks = apply_project_type(checks, project_type)
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


def _collect_recommendations(checks: list[CheckResult]) -> list[str]:
    return list(dict.fromkeys(item for check in checks for item in check.recommendations))[:8]
