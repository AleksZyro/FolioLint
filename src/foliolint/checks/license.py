from __future__ import annotations

from pathlib import Path

from foliolint.check_metadata import LICENSE
from foliolint.config import ShowcaseConfig
from foliolint.models import CheckResult


def check_license(path: Path, config: ShowcaseConfig) -> CheckResult:
    del config
    names = {child.name.upper() for child in path.iterdir() if child.is_file()}
    found = any(name in names for name in {"LICENSE", "LICENCE", "COPYING"})
    if found:
        return CheckResult(
            category=LICENSE.category,
            status="ok",
            message="License file found.",
            points=10,
            max_points=LICENSE.max_points,
            details={"found": True},
            explanation="License gets 10/10 because LICENSE, LICENCE or COPYING exists.",
        )
    return CheckResult(
        category=LICENSE.category,
        status="warning",
        message="No LICENSE, LICENCE or COPYING file found.",
        points=0,
        max_points=LICENSE.max_points,
        details={"found": False},
        explanation="License gets 0/10 because no license file was found.",
        recommendations=["Add or document the license decision before sharing publicly."],
    )
