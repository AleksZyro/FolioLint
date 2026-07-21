from pathlib import Path

from foliolint.checks import check_demo, check_media
from foliolint.config import ShowcaseConfig


def test_media_check_warns_without_media(tmp_path: Path) -> None:
    result = check_media(tmp_path, ShowcaseConfig())

    assert result.status == "warning"
    assert result.points == 0


def test_media_check_finds_screenshot(tmp_path: Path) -> None:
    assets = tmp_path / "docs" / "assets"
    assets.mkdir(parents=True)
    (assets / "screenshot.png").write_bytes(b"fake image")

    result = check_media(tmp_path, ShowcaseConfig())

    assert result.status == "ok"
    assert result.points == 10


def test_demo_check_detects_github_pages_and_localhost(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        "Demo: https://example.github.io/tool\nLocal: http://localhost:8000\n",
        encoding="utf-8",
    )

    result = check_demo(tmp_path, ShowcaseConfig())

    assert result.status == "ok"
    assert result.details["hosted_demo"] is True
    assert result.details["local_demo"] is True

