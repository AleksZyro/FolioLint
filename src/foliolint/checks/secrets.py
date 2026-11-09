from __future__ import annotations

import re
from pathlib import Path

from foliolint.check_metadata import SECRETS
from foliolint.checks.common import GENERATED_DIRS, _iter_files, _read_text
from foliolint.config import ShowcaseConfig
from foliolint.models import CheckResult


def check_secrets(path: Path, config: ShowcaseConfig) -> CheckResult:
    matches: list[dict[str, str]] = []
    for file in _iter_files(path, config, skip_dirs=SECRET_SCAN_SKIP_DIRS):
        if not _should_scan_text(file):
            continue
        match = _find_secret_hint(_read_text(file))
        if match is None:
            continue
        pattern, line = match
        matches.append(
            {"path": file.relative_to(path).as_posix(), "pattern": pattern, "line": str(line)}
        )
        if len(matches) == 20:
            break

    if matches:
        message = "Obvious secret risk hints found."
        explanation = "Secrets gets 0/10 because obvious risky strings were found."
        recommendations = [
            "Review obvious secret risk hints before sharing the repository publicly."
        ]
    else:
        message = "No obvious secret patterns found."
        explanation = "Secrets gets 10/10 because no configured risky strings were found."
        recommendations = []
    return CheckResult(
        category=SECRETS.category,
        status="warning" if matches else "ok",
        message=message,
        points=0 if matches else SECRETS.max_points,
        max_points=SECRETS.max_points,
        details={"matches": matches},
        explanation=f"{explanation} This is not a full security scan.",
        recommendations=recommendations,
    )


def _should_scan_text(file: Path) -> bool:
    if file.suffix.lower() not in TEXT_EXTENSIONS and file.name != ".env":
        return False
    try:
        return file.stat().st_size <= 1024 * 1024
    except OSError:
        return False


def _find_secret_hint(text: str) -> tuple[str, int] | None:
    private_key_marker = "BEGIN " + "RSA PRIVATE KEY"
    for line_number, line in enumerate(text.splitlines(), start=1):
        if line.lstrip().startswith(("#", "//", "<!--", ";")):
            continue
        if private_key_marker in line.upper():
            return private_key_marker, line_number
        match = SECRET_ASSIGNMENT_RE.search(line)
        if match:
            return match.group("name").upper(), line_number
    return None


SECRET_SCAN_SKIP_DIRS = GENERATED_DIRS | {".ruff_cache", ".venv", "venv", "site-packages"}


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
