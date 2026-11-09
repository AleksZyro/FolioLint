import json
from io import StringIO
from pathlib import Path

import pytest
from rich.console import Console
from typer.testing import CliRunner

from foliolint.cli import app
from foliolint.models import CheckResult, ScanReport
from foliolint.report import render_html_report, render_text_report


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


def test_html_report_contains_remote_scan_context() -> None:
    report = ScanReport(
        path="C:/Temp/repository",
        checks=[CheckResult("README", "ok", "README found", 25, 25)],
        recommendations=[],
        score=100,
        status="Showcase-ready",
        remote={
            "source_url": "https://github.com/example/project",
            "branch": "main",
        },
    )

    html = render_html_report(report)

    assert "https://github.com/example/project" in html
    assert "branch <code>main</code>" in html
    assert "Temporary copy: removed after scan" in html


def test_html_report_escapes_repository_evidence_and_omits_disabled_score() -> None:
    report = ScanReport(
        path="<repo>",
        checks=[
            CheckResult(
                "Media",
                "warning",
                "<script>file</script>",
                0,
                10,
                details={"media_files": ["<image>.png"]},
            )
        ],
        recommendations=["Review <image>.png"],
        score=25,
    )

    html = render_html_report(report, details=True, include_score=False)

    assert 'class="score"' not in html
    assert "<script>" not in html
    assert "&lt;repo&gt;" in html
    assert "&lt;script&gt;file&lt;/script&gt;" in html
    assert "<li>media_files: &lt;image&gt;.png</li>" in html
    assert "<li>Review &lt;image&gt;.png</li>" in html


@pytest.mark.parametrize("width", [42, 100])
def test_text_report_keeps_status_and_literal_evidence_without_color(width: int) -> None:
    report = ScanReport(
        path="repo/[example]",
        checks=[CheckResult("Media", "warning", "Review [bold].png", 0, 10)],
        recommendations=[],
        score=25,
        status="Not ready",
    )
    buffer = StringIO()
    render_text_report(
        report, explain=True, console=Console(file=buffer, width=width, color_system=None)
    )

    output = buffer.getvalue()
    assert "Score: 25/100" in output
    assert "Warning" in output
    assert "0/10" in output
    assert "Review [bold].png" in output
    assert "\x1b" not in output


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
