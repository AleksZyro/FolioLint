from __future__ import annotations

from pathlib import Path

from foliolint.check_metadata import LICENSE
from foliolint.config import ShowcaseConfig
from foliolint.models import CheckResult


def check_license(path: Path, config: ShowcaseConfig) -> CheckResult:
    del config
    found = any(
        child.name.upper() in {"LICENSE", "LICENCE", "COPYING"} and child.is_file()
        for child in path.iterdir()
    )
    if found:
        message = "License file found."
        explanation = "License gets 10/10 because LICENSE, LICENCE or COPYING exists."
    else:
        message = "No LICENSE, LICENCE or COPYING file found."
        explanation = "License gets 0/10 because no license file was found."
    return CheckResult(
        category=LICENSE.category,
        status="ok" if found else "warning",
        message=message,
        points=LICENSE.max_points if found else 0,
        max_points=LICENSE.max_points,
        details={"found": found},
        explanation=explanation,
        recommendations=[]
        if found
        else ["Add or document the license decision before sharing publicly."],
    )
