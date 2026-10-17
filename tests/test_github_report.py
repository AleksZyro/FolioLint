from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from foliolint.cli import app
from foliolint.github_report import render_github_report
from foliolint.models import CheckResult, ScanReport
from foliolint.scanner import scan_project


def test_missing_files_have_no_invented_annotations(tmp_path: Path) -> None:
    result = CliRunner().invoke(app, ["scan", str(tmp_path), "--format", "github"])
    assert result.exit_code == 0
    assert "::warning" not in result.stdout
    assert "FolioLint warning: README: No README.md" in result.stdout
    assert "FolioLint score: 25/100" in result.stdout


def test_annotations_use_existing_readme_and_secret_line(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Example\n", encoding="utf-8")
    (tmp_path / "settings.py").write_text('\nAPI_KEY = "placeholder"\n', encoding="utf-8")
    result = CliRunner().invoke(app, ["scan", str(tmp_path), "--format", "github"])
    assert result.exit_code == 0
    assert "::warning file=README.md::README:" in result.stdout
    assert "::warning file=settings.py,line=2::Secrets:" in result.stdout
    assert "placeholder" not in result.stdout
    assert "file=LICENSE" not in result.stdout


def test_workflow_command_escaping_prevents_extra_commands() -> None:
    check = CheckResult(
        "Secrets",
        "warning",
        "100%\r\n::error::injected",
        0,
        10,
        details={"matches": [{"path": "a,b:c%\r\n.py", "line": "3"}]},
    )
    output = render_github_report(ScanReport(".", [check], []), include_score=False)
    assert output == (
        "::warning file=a%2Cb%3Ac%25%0D%0A.py,line=3::Secrets: 100%25%0D%0A::error::injected\n"
    )
    assert len(output.splitlines()) == 1


def test_hygiene_annotates_files_but_not_directories() -> None:
    check = CheckResult(
        "Hygiene",
        "warning",
        "Review files",
        3,
        15,
        details={
            "generated_dirs": ["dist"],
            "env_files": [".env"],
            "large_files": [".env"],
            "log_files": ["run.log"],
        },
    )
    output = render_github_report(ScanReport(".", [check], []), include_score=False)
    assert output.count("file=.env::") == 1
    assert "file=run.log::" in output
    assert "file=dist" not in output


@pytest.mark.parametrize("ignored", [False, True])
def test_github_respects_ignore_checks_and_paths(tmp_path: Path, ignored: bool) -> None:
    (tmp_path / "settings.py").write_text('TOKEN = "placeholder"', encoding="utf-8")
    setting = 'checks = ["secrets"]' if ignored else 'paths = ["settings.py"]'
    (tmp_path / ".foliolint.toml").write_text(f"[ignore]\n{setting}\n", encoding="utf-8")
    output = render_github_report(scan_project(tmp_path))
    assert "file=settings.py" not in output


def test_remote_warnings_do_not_annotate_local_checkout(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Example", encoding="utf-8")
    report = replace(scan_project(tmp_path), remote={"source_url": "https://github.com/a/b"})
    output = render_github_report(report)
    assert "::warning" not in output
    assert "FolioLint warning: README:" in output


def test_scan_url_github_format_uses_shared_renderer(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "README.md").write_text("# Example", encoding="utf-8")
    cleaned_up = []

    @contextmanager
    def prepare(*args, **kwargs):
        try:
            yield SimpleNamespace(path=tmp_path, branch="main")
        finally:
            cleaned_up.append(True)

    monkeypatch.setattr("foliolint.cli.prepare_remote_repository", prepare)
    result = CliRunner().invoke(
        app,
        [
            "scan-url",
            "https://github.com/example/project",
            "--format",
            "github",
            "--fail-under",
            "100",
        ],
    )
    assert result.exit_code == 1
    assert "::warning" not in result.stdout
    assert "FolioLint warning: README:" in result.stdout
    assert cleaned_up == [True]


def test_github_format_threshold_and_file_output(tmp_path: Path) -> None:
    target = tmp_path / "report.txt"
    result = CliRunner().invoke(
        app,
        [
            "scan",
            str(tmp_path),
            "--format",
            "github",
            "--fail-under",
            "75",
            "--output",
            str(target),
        ],
    )
    assert result.exit_code == 1
    assert "FolioLint score: 25/100" in target.read_text(encoding="utf-8")


def test_github_no_score_and_invalid_threshold_combination(tmp_path: Path) -> None:
    runner = CliRunner()
    args = ["scan", str(tmp_path), "--format", "github", "--no-score"]
    result = runner.invoke(app, args)
    assert result.exit_code == 0
    assert "score:" not in result.stdout
    assert runner.invoke(app, [*args, "--fail-under", "75"]).exit_code == 2
