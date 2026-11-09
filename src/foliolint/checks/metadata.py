from __future__ import annotations

from pathlib import Path

from foliolint.check_metadata import METADATA
from foliolint.checks.common import _workflow_files
from foliolint.checks.project_type import detect_project_type
from foliolint.config import ShowcaseConfig
from foliolint.models import CheckResult


def check_metadata(path: Path, config: ShowcaseConfig) -> CheckResult:
    del config
    workflows = _workflow_files(path)
    project_type, type_evidence = detect_project_type(path)
    found = {
        "pyproject.toml": (path / "pyproject.toml").exists(),
        "requirements.txt": (path / "requirements.txt").exists(),
        "package.json": (path / "package.json").exists(),
        "vite.config": any(path.glob("vite.config.*")),
        ".github/workflows": bool(workflows),
        "workflow_files": [file.relative_to(path).as_posix() for file in workflows],
        "project_type": project_type,
        "project_type_evidence": type_evidence,
    }
    points = 0
    if found["pyproject.toml"]:
        points += 2
    for key in ["requirements.txt", "package.json", "vite.config", ".github/workflows"]:
        if found[key]:
            points += 1
    points = min(points, 5)
    status = "ok" if points > 0 else "warning"
    if project_type:
        message = f"{project_type} project metadata found."
    else:
        message = "Project metadata found." if points > 0 else "No common project metadata found."
    recommendations = (
        []
        if points > 0
        else ["Add common project metadata such as pyproject.toml or package.json."]
    )
    return CheckResult(
        category=METADATA.category,
        status=status,
        message=message,
        points=points,
        max_points=METADATA.max_points,
        details=found,
        explanation=(
            f"Metadata gets {points}/5 from common project files and workflow metadata. "
            f"Detected project type: {project_type or 'unknown'}."
        ),
        recommendations=recommendations,
    )
