from __future__ import annotations

import json
import tomllib
from pathlib import Path


def detect_project_type(path: Path) -> tuple[str | None, list[str]]:
    """Return a simple project type and the files that support the detection."""
    evidence: list[str] = []
    package_path = path / "package.json"
    package_name = ""
    package_scripts: dict[str, object] = {}
    if package_path.exists():
        evidence.append("package.json")
        try:
            package = json.loads(package_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            package = {}
        if isinstance(package, dict):
            package_name = " ".join(
                str(value) for value in package.get("dependencies", {}) if isinstance(value, str)
            ).lower()
            package_name += (
                " "
                + " ".join(
                    str(value)
                    for value in package.get("devDependencies", {})
                    if isinstance(value, str)
                ).lower()
            )
            package_scripts = package.get("scripts", {})
            if not isinstance(package_scripts, dict):
                package_scripts = {}

    vite_files = list(path.glob("vite.config.*"))
    has_react = (
        "react" in package_name or any(path.glob("*.jsx")) or any((path / "src").glob("*.jsx"))
    )
    if vite_files:
        evidence.append(vite_files[0].name)
        if has_react:
            return "react", evidence
        return "vite", evidence
    if has_react:
        return "react", evidence
    if package_path.exists():
        if package.get("bin"):
            evidence.append("package.json bin")
            return "node-cli", evidence
        if package_scripts:
            evidence.append("package.json scripts")
        return "node", evidence
    pyproject_path = path / "pyproject.toml"
    if pyproject_path.exists():
        evidence.append("pyproject.toml")
        pyproject = _read_pyproject(pyproject_path)
        project = pyproject.get("project", {})
        if isinstance(project, dict) and isinstance(project.get("scripts"), dict):
            evidence.append("pyproject.toml project.scripts")
            return "python-cli", evidence
        return "python", evidence
    if (path / "requirements.txt").exists():
        evidence.append("requirements.txt")
        return "python", evidence
    if list(path.glob("*.html")):
        evidence.append("HTML entrypoint")
        return "static-web", evidence
    return None, evidence


def _read_pyproject(path: Path) -> dict[str, object]:
    try:
        with path.open("rb") as file:
            data = tomllib.load(file)
    except (OSError, tomllib.TOMLDecodeError):
        return {}
    return data if isinstance(data, dict) else {}
