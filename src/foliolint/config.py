from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

CONFIG_FILE = ".foliolint.toml"
DEFAULT_CONFIG = """# Optional FolioLint configuration

[ignore]
# paths = ["dist", "docs/assets/large-demo.mp4"]
# checks = ["demo-link"]

[thresholds]
large_file_mb = 5

[project]
# type = "web-app"
"""


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

    ignore = raw.get("ignore", {})
    large_file_mb = raw.get("thresholds", {}).get("large_file_mb", 5)
    if not isinstance(large_file_mb, int) or large_file_mb < 1:
        large_file_mb = 5
    project_type = raw.get("project", {}).get("type")
    return ShowcaseConfig(
        ignore=IgnoreConfig(
            paths=_string_list(ignore.get("paths")),
            checks=_string_list(ignore.get("checks")),
        ),
        thresholds=Thresholds(large_file_mb=large_file_mb),
        project=ProjectConfig(type=project_type if isinstance(project_type, str) else None),
    )


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]
