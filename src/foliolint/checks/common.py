from __future__ import annotations

import re
from collections.abc import Iterable
from os import scandir
from pathlib import Path

from foliolint.config import ShowcaseConfig
from foliolint.paths import directory, regular_file


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
                if entry.is_symlink():
                    continue
                if entry.is_dir(follow_symlinks=False):
                    if not directory(item):
                        continue
                    if skip_dirs and entry.name in skip_dirs:
                        continue
                    children.append(item)
                elif not regular_file(item):
                    continue
                yield item
        pending.extend(reversed(children))


def _ignored_paths(config: ShowcaseConfig) -> set[str]:
    return {entry.strip("/\\") for entry in config.ignore.paths}


def _read_text(path: Path) -> str:
    if not regular_file(path):
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _has_any_term(text: str, terms: list[str]) -> bool:
    return any(re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text) for term in terms)


def _workflow_files(path: Path) -> list[Path]:
    workflows = path / ".github" / "workflows"
    if not directory(path / ".github") or not directory(workflows):
        return []
    return [
        file
        for file in workflows.iterdir()
        if file.suffix in {".yml", ".yaml"} and regular_file(file)
    ]


GENERATED_DIRS = {"dist", "build", "_site", "node_modules", "__pycache__", ".pytest_cache"}
