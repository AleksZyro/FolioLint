from pathlib import Path

from foliolint.checks import check_license
from foliolint.config import ShowcaseConfig


def test_license_check_missing_license(tmp_path: Path) -> None:
    result = check_license(tmp_path, ShowcaseConfig())

    assert result.status == "warning"
    assert result.points == 0
    assert "No LICENSE" in result.message


def test_license_check_accepts_copying(tmp_path: Path) -> None:
    (tmp_path / "COPYING").write_text("license text\n", encoding="utf-8")

    result = check_license(tmp_path, ShowcaseConfig())

    assert result.status == "ok"
    assert result.points == result.max_points
