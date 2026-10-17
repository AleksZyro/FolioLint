from __future__ import annotations

import re
from pathlib import Path

from foliolint.check_metadata import SECRETS
from foliolint.checks.common import GENERATED_DIRS, _iter_files, _read_text
from foliolint.config import ShowcaseConfig
from foliolint.models import CheckResult


def check_secrets(path: Path, config: ShowcaseConfig) -> CheckResult:
    matches: list[dict[str, str]] = []
    for file in _iter_files(path, config):
        if _is_in_skipped_secret_dir(file, path):
            continue
        if not _should_scan_text(file):
            continue
        text = _read_text(file)
        if not text:
            continue
        match = _find_secret_hint(text)
        if match is not None:
            matches.append(
                {
                    "path": file.relative_to(path).as_posix(),
                    "pattern": match["pattern"],
                    "line": str(match["line"]),
                }
            )

    if matches:
        return CheckResult(
            category=SECRETS.category,
            status="warning",
            message="Obvious secret risk hints found.",
            points=0,
            max_points=SECRETS.max_points,
            details={"matches": matches[:20]},
            explanation=(
                "Secrets gets 0/10 because obvious risky strings were found. "
                "This is not a full security scan."
            ),
            recommendations=[
                "Review obvious secret risk hints before sharing the repository publicly."
            ],
        )
    return CheckResult(
        category=SECRETS.category,
        status="ok",
        message="No obvious secret patterns found.",
        points=10,
        max_points=SECRETS.max_points,
        details={"matches": []},
        explanation=(
            "Secrets gets 10/10 because no configured risky strings were found. "
            "This is not a full security scan."
        ),
    )


def _should_scan_text(file: Path) -> bool:
    if file.suffix.lower() not in TEXT_EXTENSIONS and file.name not in {".env"}:
        return False
    try:
        return file.stat().st_size <= 1024 * 1024
    except OSError:
        return False


def _is_in_skipped_secret_dir(file: Path, root: Path) -> bool:
    try:
        relative_parts = file.relative_to(root).parts
    except ValueError:
        return False
    return any(part in SECRET_SCAN_SKIP_DIRS for part in relative_parts[:-1])


def _find_secret_hint(text: str) -> dict[str, int | str] | None:
    private_key_marker = "BEGIN " + "RSA PRIVATE KEY"
    for line_number, line in enumerate(text.splitlines(), start=1):
        if _is_comment_line(line):
            continue
        if private_key_marker in line.upper():
            return {"pattern": private_key_marker, "line": line_number}
        match = SECRET_ASSIGNMENT_RE.search(line)
        if match:
            return {"pattern": match.group("name").upper(), "line": line_number}
    return None


def _is_comment_line(line: str) -> bool:
    stripped = line.lstrip()
    return stripped.startswith(("#", "//", "<!--", ";"))


SECRET_SCAN_SKIP_DIRS = GENERATED_DIRS | {".ruff_cache", ".venv", "venv", "site-packages"}


SECRET_PATTERNS = [
    "API" + "_KEY",
    "SECRET",
    "TOKEN",
    "PASSWORD",
    "PRIVATE" + "_KEY",
    "BEGIN " + "RSA PRIVATE KEY",
]


SECRET_ASSIGNMENT_RE = re.compile(
    (
        r"(?<![-\w])(?P<name>(?:[A-Z0-9]+_){0,4}"
        r"(?:API_KEY|SECRET|TOKEN|PASSWORD|PRIVATE_KEY))(?![-\w])\s*[:=]"
    ),
    re.IGNORECASE,
)


TEXT_EXTENSIONS = {
    ".cfg",
    ".css",
    ".env",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".jsx",
    ".md",
    ".py",
    ".sh",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}
