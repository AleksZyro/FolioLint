from __future__ import annotations

import re
from collections.abc import Iterable
from os import scandir
from pathlib import Path

from foliolint.config import ShowcaseConfig


def _iter_files(
    path: Path, config: ShowcaseConfig, *, skip_dirs: set[str] | None = None
) -> Iterable[Path]:
    for item in _iter_paths(path, config, skip_dirs=skip_dirs):
        if item.is_file():
            yield item


def _iter_paths(
    path: Path, config: ShowcaseConfig, *, skip_dirs: set[str] | None = None
) -> Iterable[Path]:
    """Yield each directory's entries before descending, as Path.rglob does."""
    if ".git" in path.parts:
        return
    ignored = _ignored_paths(config)
    pending = [path]
    while pending:
        folder = pending.pop()
        try:
            entries = scandir(folder)
        except (PermissionError, FileNotFoundError, NotADirectoryError):
            continue
        children = []
        with entries:
            for entry in entries:
                if entry.name == ".git":
                    continue
                item = folder / entry.name
                if ignored and item.relative_to(path).as_posix() in ignored:
                    continue
                if entry.is_dir(follow_symlinks=False):
                    if skip_dirs and entry.name in skip_dirs:
                        continue
                    children.append(item)
                yield item
        pending.extend(reversed(children))


def _ignored_paths(config: ShowcaseConfig) -> set[str]:
    return {entry.strip("/\\") for entry in config.ignore.paths}


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _has_any(text: str, needles: list[str]) -> bool:
    return any(needle in text for needle in needles)


def _has_any_term(text: str, terms: list[str]) -> bool:
    return any(re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text) for term in terms)


def _workflow_files(path: Path) -> list[Path]:
    workflows = path / ".github" / "workflows"
    if not workflows.is_dir():
        return []
    return [
        file for file in workflows.iterdir() if file.suffix in {".yml", ".yaml"} and file.is_file()
    ]


GENERATED_DIRS = {"dist", "build", "_site", "node_modules", "__pycache__", ".pytest_cache"}
