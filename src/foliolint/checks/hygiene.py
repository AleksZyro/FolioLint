from __future__ import annotations

import subprocess
from pathlib import Path

from foliolint.check_metadata import HYGIENE
from foliolint.checks.common import GENERATED_DIRS, _iter_paths, _read_text
from foliolint.config import ShowcaseConfig
from foliolint.models import CheckResult


def check_hygiene(path: Path, config: ShowcaseConfig) -> CheckResult:
    generated_dirs: set[str] = set()
    ignored_local_paths: list[str] = []
    env_files: list[str] = []
    log_files: list[str] = []
    large_files: list[str] = []
    threshold_bytes = config.thresholds.large_file_mb * 1024 * 1024
    gitignore_patterns = _read_gitignore_patterns(path)
    tracked_paths = _git_tracked_paths(path)

    for item in _iter_paths(path, config):
        rel = item.relative_to(path).as_posix()
        if tracked_paths is not None:
            is_untracked_hygiene_path = _is_common_hygiene_path(item) and not _is_git_tracked(
                rel, item.is_dir(), tracked_paths
            )
            if is_untracked_hygiene_path:
                ignored_local_paths.append(rel)
                continue
        else:
            if _matches_gitignore(rel, item.is_dir(), gitignore_patterns):
                if _is_common_hygiene_path(item):
                    ignored_local_paths.append(rel)
                continue
        if item.is_dir() and item.name in GENERATED_DIRS:
            generated_dirs.add(rel)
            continue
        if not item.is_file():
            continue
        if item.name == ".env" or item.name.startswith(".env."):
            env_files.append(rel)
        if item.suffix.lower() == ".log":
            log_files.append(rel)
        try:
            if item.stat().st_size > threshold_bytes:
                large_files.append(rel)
        except OSError:
            continue

    penalties = min(6, len(generated_dirs) * 2)
    penalties += min(4, len(large_files) * 3)
    penalties += min(4, len(env_files) * 4)
    penalties += min(3, len(log_files) * 2)
    points = max(0, 15 - penalties)
    has_issues = bool(generated_dirs or env_files or log_files or large_files)
    message = "No common hygiene issues found."
    recommendations = []
    if has_issues:
        parts = []
        if generated_dirs:
            parts.append(f"generated folders: {', '.join(sorted(generated_dirs)[:3])}")
            recommendations.append(
                "Remove generated folders from the repository if they are not needed."
            )
        if large_files:
            parts.append(f"large files: {', '.join(large_files[:3])}")
            recommendations.append(
                "Review large files and move heavy demo assets out of git if needed."
            )
        if env_files:
            parts.append(f"env files: {', '.join(env_files[:3])}")
            recommendations.append(
                "Remove .env files from the repository and keep local settings private."
            )
        if log_files:
            parts.append(f"log files: {', '.join(log_files[:3])}")
            recommendations.append("Remove log files unless they are intentional fixtures.")
        message = "; ".join(parts)
    return CheckResult(
        category=HYGIENE.category,
        status="warning" if has_issues else "ok",
        message=message,
        points=points,
        max_points=HYGIENE.max_points,
        details={
            "generated_dirs": sorted(generated_dirs),
            "large_files": large_files,
            "env_files": env_files,
            "log_files": log_files,
            "ignored_local_paths": ignored_local_paths[:20],
            "uses_git_tracking": tracked_paths is not None,
            "large_file_mb": config.thresholds.large_file_mb,
        },
        explanation=(
            f"Hygiene gets {points}/15 after deductions for generated folders, "
            "large files, env files and logs."
        ),
        recommendations=recommendations,
    )


def _read_gitignore_patterns(root: Path) -> list[str]:
    gitignore = root / ".gitignore"
    if not gitignore.exists():
        return []
    patterns: list[str] = []
    for line in _read_text(gitignore).splitlines():
        pattern = line.strip()
        if not pattern or pattern.startswith("#") or pattern.startswith("!"):
            continue
        patterns.append(pattern)
    return patterns


def _matches_gitignore(rel_path: str, is_dir: bool, patterns: list[str]) -> bool:
    parts = rel_path.split("/")
    for pattern in patterns:
        normalized = pattern.strip("/")
        if not normalized:
            continue
        dir_only = pattern.endswith("/")
        if dir_only and not is_dir:
            parent_parts = parts[:-1]
            if "/" not in normalized and normalized in parent_parts:
                return True
            if "/".join(parent_parts).startswith(f"{normalized}/"):
                return True
            continue
        if "/" not in normalized and normalized in parts:
            return True
        if rel_path == normalized or rel_path.startswith(f"{normalized}/"):
            return True
    return False


def _is_common_hygiene_path(item: Path) -> bool:
    return (
        item.name in GENERATED_DIRS
        or item.name == ".env"
        or item.name.startswith(".env.")
        or item.suffix.lower() == ".log"
    )


def _git_tracked_paths(root: Path) -> set[str] | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None

    paths = {path for path in result.stdout.split("\0") if path}
    return paths


def _is_git_tracked(rel_path: str, is_dir: bool, tracked_paths: set[str]) -> bool:
    if rel_path in tracked_paths:
        return True
    if is_dir:
        return any(path.startswith(f"{rel_path}/") for path in tracked_paths)
    return False
