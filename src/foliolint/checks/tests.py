from __future__ import annotations

import json
from pathlib import Path

from foliolint.check_metadata import TESTS
from foliolint.checks.common import _is_ignored, _iter_files, _read_text
from foliolint.config import ShowcaseConfig
from foliolint.models import CheckResult


def check_tests(path: Path, config: ShowcaseConfig) -> CheckResult:
    files = list(_iter_files(path, config))
    has_tests_dir = (path / "tests").is_dir() and not _is_ignored(path / "tests", path, config)
    test_files = []
    for file in files:
        if _is_test_file(file):
            test_files.append(file)
    package_test = _package_json_has_test_script(path / "package.json")
    github_actions_details = _github_actions_details(path)
    github_actions = github_actions_details["has_meaningful_checks"]
    points = 0
    if has_tests_dir:
        points += 5
    if test_files:
        points += 5
    if package_test:
        points += 2
    if github_actions:
        points += 3
    details = {
        "tests_dir": has_tests_dir,
        "test_files": [file.relative_to(path).as_posix() for file in test_files[:10]],
        "package_json_test_script": package_test,
        "github_actions": github_actions,
        "github_actions_files": github_actions_details["files"],
        "github_actions_tools": github_actions_details["tools"],
    }
    status = "ok" if points >= 8 else "warning"
    message = "Test setup detected." if points >= 8 else "No clear test setup detected."
    recommendations = []
    if not test_files:
        recommendations.append(
            "Add test files such as test_*.py, *_test.py, *.test.js or *.spec.ts."
        )
    if not github_actions:
        recommendations.append(
            "Add a GitHub Actions workflow that runs pytest, ruff or another test command."
        )
    return CheckResult(
        category=TESTS.category,
        status=status,
        message=message,
        points=points,
        max_points=TESTS.max_points,
        details=details,
        explanation=(
            f"Tests gets {points}/15 from tests folder, test files, "
            "package test script and GitHub Actions."
        ),
        recommendations=recommendations,
    )


def _package_json_has_test_script(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        package = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    scripts = package.get("scripts", {})
    return isinstance(scripts, dict) and isinstance(scripts.get("test"), str)


def _is_test_file(file: Path) -> bool:
    name = file.name.lower()
    if file.suffix == ".py" and (name.startswith("test_") or name.endswith("_test.py")):
        return True
    return any(name.endswith(suffix) for suffix in TEST_FILE_SUFFIXES)


def _github_actions_details(path: Path) -> dict[str, object]:
    workflows = path / ".github" / "workflows"
    if not workflows.is_dir():
        return {"files": [], "tools": [], "has_meaningful_checks": False}

    workflow_files = [
        file for file in workflows.iterdir() if file.is_file() and file.suffix in {".yml", ".yaml"}
    ]
    tools: set[str] = set()
    for file in workflow_files:
        text = _read_text(file).lower()
        for tool, hints in WORKFLOW_HINTS.items():
            if any(hint in text for hint in hints):
                tools.add(tool)

    return {
        "files": [file.relative_to(path).as_posix() for file in workflow_files],
        "tools": sorted(tools),
        "has_meaningful_checks": bool(tools),
    }


TEST_FILE_SUFFIXES = (
    ".test.js",
    ".test.jsx",
    ".test.ts",
    ".test.tsx",
    ".spec.js",
    ".spec.jsx",
    ".spec.ts",
    ".spec.tsx",
)


WORKFLOW_HINTS = {
    "pytest": ["pytest"],
    "ruff": ["ruff check", "ruff format", "ruff"],
    "python": ["python-version", "setup-python", "python -m", "python"],
    "npm_test": ["npm test", "npm run test"],
}
