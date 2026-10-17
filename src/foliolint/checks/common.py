from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path

from foliolint.config import ShowcaseConfig


def _iter_files(path: Path, config: ShowcaseConfig) -> Iterable[Path]:
    for item in _iter_paths(path, config):
        if item.is_file():
            yield item


def _iter_paths(path: Path, config: ShowcaseConfig) -> Iterable[Path]:
    for item in path.rglob("*"):
        if ".git" in item.parts:
            continue
        if _is_ignored(item, path, config):
            continue
        yield item


def _is_ignored(item: Path, root: Path, config: ShowcaseConfig) -> bool:
    try:
        rel = item.relative_to(root).as_posix()
    except ValueError:
        return False
    ignored = {entry.strip("/\\") for entry in config.ignore.paths}
    return any(rel == entry or rel.startswith(f"{entry}/") for entry in ignored if entry)


def _read_text(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _has_any(text: str, needles: list[str]) -> bool:
    return any(needle in text for needle in needles)


def _has_any_term(text: str, terms: list[str]) -> bool:
    return any(re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text) for term in terms)


GENERATED_DIRS = {"dist", "build", "_site", "node_modules", "__pycache__", ".pytest_cache"}
