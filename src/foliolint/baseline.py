from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from foliolint.models import ScanReport


def save_baseline(report: ScanReport, path: Path) -> None:
    data = {
        "score": report.score,
        "status": report.status,
        "checks": [
            {
                "category": check.category,
                "status": check.status,
                "points": check.points,
                "max_points": check.max_points,
            }
            for check in report.checks
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_baseline(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Could not read baseline file: {path}") from error
    if not isinstance(data, dict) or not isinstance(data.get("checks"), list):
        raise ValueError(f"Invalid FolioLint baseline file: {path}")
    return data


def compare_baseline(report: ScanReport, baseline: dict[str, Any]) -> dict[str, Any]:
    old_checks = {
        item.get("category"): item
        for item in baseline["checks"]
        if isinstance(item, dict) and isinstance(item.get("category"), str)
    }
    new_checks = {check.category: check for check in report.checks}
    changed: list[dict[str, Any]] = []
    for category, check in new_checks.items():
        previous = old_checks.get(category)
        if previous is None:
            changed.append({"category": category, "change": "added", "status": check.status})
            continue
        if (
            previous.get("status") != check.status
            or previous.get("points") != check.points
            or previous.get("max_points") != check.max_points
        ):
            changed.append(
                {
                    "category": category,
                    "change": "changed",
                    "from": {
                        "status": previous.get("status"),
                        "points": previous.get("points"),
                        "max_points": previous.get("max_points"),
                    },
                    "to": {
                        "status": check.status,
                        "points": check.points,
                        "max_points": check.max_points,
                    },
                }
            )
    for category in old_checks.keys() - new_checks.keys():
        changed.append({"category": category, "change": "removed"})

    old_score = baseline.get("score")
    score_delta = (
        report.score - old_score
        if isinstance(old_score, int) and isinstance(report.score, int)
        else None
    )
    return {
        "baseline_score": old_score,
        "current_score": report.score,
        "score_delta": score_delta,
        "changed_checks": changed,
    }
