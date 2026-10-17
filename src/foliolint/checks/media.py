from __future__ import annotations

from pathlib import Path

from foliolint.check_metadata import MEDIA
from foliolint.checks.common import _has_any, _iter_files, _read_text
from foliolint.config import ShowcaseConfig
from foliolint.models import CheckResult


def check_media(path: Path, config: ShowcaseConfig) -> CheckResult:
    media_files = []
    for file in _iter_files(path, config):
        rel = file.relative_to(path).as_posix()
        in_media_dir = any(rel.startswith(f"{media_dir}/") for media_dir in MEDIA_DIRS)
        if in_media_dir and file.suffix.lower() in MEDIA_EXTENSIONS:
            media_files.append(rel)

    readme_text = _read_text(path / "README.md").lower()
    readme_mentions_media = _has_any(
        readme_text,
        [".png", ".jpg", ".jpeg", ".gif", ".mp4", ".webm", "screenshot", "demo", "!["],
    )
    found = bool(media_files) or readme_mentions_media
    if found:
        return CheckResult(
            category=MEDIA.category,
            status="ok",
            message="Screenshot or demo media hint found.",
            points=10,
            max_points=MEDIA.max_points,
            details={
                "media_files": media_files[:20],
                "readme_mentions_media": readme_mentions_media,
            },
            explanation=(
                "Media gets 10/10 because media files or README media references were found."
            ),
        )
    return CheckResult(
        category=MEDIA.category,
        status="warning",
        message="No screenshots or demo media found.",
        points=0,
        max_points=MEDIA.max_points,
        details={"media_files": [], "readme_mentions_media": False},
        explanation="Media gets 0/10 because no media file or README media reference was found.",
        recommendations=[
            "Add a screenshot or short demo media under docs/assets/ when it helps the project."
        ],
    )


MEDIA_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".mp4", ".webm"}


MEDIA_DIRS = {"docs/assets", "assets", "public"}
