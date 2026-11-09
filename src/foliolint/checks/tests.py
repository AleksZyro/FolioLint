from __future__ import annotations

from itertools import islice
from pathlib import Path

from foliolint.check_metadata import TESTS
from foliolint.checks.common import _ignored_paths, _iter_files, _read_text, _workflow_files
from foliolint.checks.project_type import _read_package_json
from foliolint.config import ShowcaseConfig
from foliolint.models import CheckResult


def check_tests(path: Path, config: ShowcaseConfig) -> CheckResult:
    has_tests_dir = "tests" not in _ignored_paths(config) and (path / "tests").is_dir()
    test_files = list(
        islice((file for file in _iter_files(path, config) if _is_test_file(file)), 10)
    )
    scripts = _read_package_json(path / "package.json").get("scripts")
    package_test = isinstance(scripts, dict) and isinstance(scripts.get("test"), str)
    workflows = _workflow_files(path)
    tools = _workflow_tools(workflows)
    github_actions = bool(tools)
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
        "test_files": [file.relative_to(path).as_posix() for file in test_files],
        "package_json_test_script": package_test,
        "github_actions": github_actions,
        "github_actions_files": [file.relative_to(path).as_posix() for file in workflows],
        "github_actions_tools": tools,
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


def _is_test_file(file: Path) -> bool:
    name = file.name.lower()
    if file.suffix == ".py" and (name.startswith("test_") or name.endswith("_test.py")):
        return True
    return any(name.endswith(suffix) for suffix in TEST_FILE_SUFFIXES)


def _workflow_tools(workflow_files: list[Path]) -> list[str]:
    tools: set[str] = set()
    for file in workflow_files:
        text = _read_text(file).lower()
        for tool, hints in WORKFLOW_HINTS.items():
            if any(hint in text for hint in hints):
                tools.add(tool)

    return sorted(tools)


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
