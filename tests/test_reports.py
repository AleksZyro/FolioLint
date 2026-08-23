import json
from pathlib import Path

from typer.testing import CliRunner

from foliolint.cli import app


def test_html_report_contains_checks_and_escapes_values(tmp_path: Path) -> None:
    runner = CliRunner()
    output_path = tmp_path / "report.html"

    result = runner.invoke(
        app,
        ["scan", str(tmp_path), "--format", "html", "--details", "--output", str(output_path)],
    )

    assert result.exit_code == 0
    html = output_path.read_text(encoding="utf-8")
    assert "<!doctype html>" in html
    assert "FolioLint Report" in html
    assert "README" in html
    assert "status-warning" in html


def test_baseline_can_be_saved_and_compared(tmp_path: Path) -> None:
    runner = CliRunner()
    baseline_path = tmp_path / "baseline.json"

    saved = runner.invoke(
        app,
        ["scan", str(tmp_path), "--save-baseline", str(baseline_path)],
    )
    assert saved.exit_code == 0
    assert baseline_path.exists()

    (tmp_path / "README.md").write_text("# Project\n\n## Installation\n", encoding="utf-8")
    compared = runner.invoke(
        app,
        [
            "scan",
            str(tmp_path),
            "--format",
            "json",
            "--compare-baseline",
            str(baseline_path),
        ],
    )

    assert compared.exit_code == 0
    data = json.loads(compared.stdout)
    assert "baseline" in data
    assert data["baseline"]["score_delta"] is not None
    assert data["baseline"]["changed_checks"]


def test_invalid_baseline_returns_clear_error(tmp_path: Path) -> None:
    baseline_path = tmp_path / "invalid.json"
    baseline_path.write_text("{}", encoding="utf-8")

    result = CliRunner().invoke(
        app,
        ["scan", str(tmp_path), "--compare-baseline", str(baseline_path)],
    )

    assert result.exit_code == 2
    assert "Invalid FolioLint baseline file" in result.stderr
