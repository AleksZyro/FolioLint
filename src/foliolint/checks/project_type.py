from __future__ import annotations

import json
import tomllib
from pathlib import Path


def detect_project_type(path: Path) -> tuple[str | None, list[str]]:
    """Return a simple project type and the files that support the detection."""
    evidence: list[str] = []
    package_path = path / "package.json"
    has_package = package_path.exists()
    package = _read_package_json(package_path) if has_package else {}
    if has_package:
        evidence.append("package.json")
    dependency_names = []
    for key in ("dependencies", "devDependencies"):
        dependencies = package.get(key)
        if isinstance(dependencies, (dict, list, str)):
            dependency_names.extend(name for name in dependencies if isinstance(name, str))

    vite_file = next(path.glob("vite.config.*"), None)
    has_react = (
        any("react" in name.lower() for name in dependency_names)
        or any(path.glob("*.jsx"))
        or any((path / "src").glob("*.jsx"))
    )
    if vite_file:
        evidence.append(vite_file.name)
        return ("react" if has_react else "vite"), evidence
    if has_react:
        return "react", evidence
    if has_package:
        if package.get("bin"):
            evidence.append("package.json bin")
            return "node-cli", evidence
        scripts = package.get("scripts")
        if isinstance(scripts, dict) and scripts:
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
    if any(path.glob("*.html")):
        evidence.append("HTML entrypoint")
        return "static-web", evidence
    return None, evidence


def _read_package_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _read_pyproject(path: Path) -> dict[str, object]:
    try:
        with path.open("rb") as file:
            return tomllib.load(file)
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return {}
