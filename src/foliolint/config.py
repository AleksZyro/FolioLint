from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

CONFIG_FILE = ".foliolint.toml"


@dataclass(frozen=True)
class Thresholds:
    large_file_mb: int = 5


@dataclass(frozen=True)
class IgnoreConfig:
    paths: list[str] = field(default_factory=list)
    checks: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ProjectConfig:
    type: str | None = None
    status: str | None = None


@dataclass(frozen=True)
class ShowcaseConfig:
    ignore: IgnoreConfig = field(default_factory=IgnoreConfig)
    thresholds: Thresholds = field(default_factory=Thresholds)
    project: ProjectConfig = field(default_factory=ProjectConfig)


def load_config(project_path: Path) -> ShowcaseConfig:
    config_path = project_path / CONFIG_FILE
    if not config_path.exists():
        return ShowcaseConfig()

    with config_path.open("rb") as file:
        raw = tomllib.load(file)

    ignore = _read_ignore(raw.get("ignore", {}))
    thresholds = _read_thresholds(raw.get("thresholds", {}))
    project = _read_project(raw.get("project", {}))
    return ShowcaseConfig(ignore=ignore, thresholds=thresholds, project=project)


def _read_ignore(raw: dict[str, Any]) -> IgnoreConfig:
    paths = _string_list(raw.get("paths", []))
    checks = _string_list(raw.get("checks", []))
    return IgnoreConfig(paths=paths, checks=checks)


def _read_thresholds(raw: dict[str, Any]) -> Thresholds:
    value = raw.get("large_file_mb", 5)
    if not isinstance(value, int) or value < 1:
        value = 5
    return Thresholds(large_file_mb=value)


def _read_project(raw: dict[str, Any]) -> ProjectConfig:
    project_type = raw.get("type")
    status = raw.get("status")
    return ProjectConfig(
        type=project_type if isinstance(project_type, str) else None,
        status=status if isinstance(status, str) else None,
    )


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]
