import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from foliolint.checks import detect_project_type
from foliolint.cli import app
from foliolint.config import CONFIG_FILE, load_config
from foliolint.scanner import scan_project


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("[project", "Could not read"),
        ("ignore = false", "[ignore] must be a table"),
        ("thresholds = 3", "[thresholds] must be a table"),
        ("project = []", "[project] must be a table"),
    ],
)
def test_scan_reports_invalid_config(tmp_path: Path, content: str, message: str) -> None:
    (tmp_path / CONFIG_FILE).write_text(content, encoding="utf-8")

    result = CliRunner().invoke(app, ["scan", str(tmp_path), "--format", "json"])

    assert result.exit_code == 2
    assert result.stdout == ""
    assert CONFIG_FILE in result.stderr
    assert message in result.stderr


def test_config_uses_defaults_without_file(tmp_path: Path) -> None:
    config = load_config(tmp_path)

    assert config.thresholds.large_file_mb == 5
    assert config.ignore.paths == []


def test_config_reads_foliolint_toml(tmp_path: Path) -> None:
    (tmp_path / ".foliolint.toml").write_text(
        """
[ignore]
paths = ["dist", "docs/assets/large-demo.mp4"]
checks = ["demo-link"]

[thresholds]
large_file_mb = 10

[project]
type = "local-app"
""",
        encoding="utf-8",
    )

    config = load_config(tmp_path)

    assert config.ignore.paths == ["dist", "docs/assets/large-demo.mp4"]
    assert config.ignore.checks == ["demo-link"]
    assert config.thresholds.large_file_mb == 10
    assert config.project.type == "local-app"


def test_config_ignored_paths_affect_hygiene(tmp_path: Path) -> None:
    (tmp_path / ".foliolint.toml").write_text(
        """
[ignore]
paths = ["dist"]
""",
        encoding="utf-8",
    )
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "bundle.log").write_text("generated\n", encoding="utf-8")

    report = scan_project(tmp_path)
    hygiene = next(check for check in report.checks if check.category == "Hygiene")

    assert hygiene.status == "ok"


def test_init_creates_example_config_without_overwriting(tmp_path: Path) -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["init", str(tmp_path)])

    assert result.exit_code == 0
    config_path = tmp_path / CONFIG_FILE
    assert config_path.exists()
    config_text = config_path.read_text(encoding="utf-8")
    assert "[thresholds]" in config_text
    assert "status" not in config_text

    second = runner.invoke(app, ["init", str(tmp_path)])

    assert second.exit_code == 2
    assert "already exists" in second.stderr


def test_init_preserves_config_created_just_before_open(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / CONFIG_FILE
    original_open = Path.open

    def open_after_concurrent_creation(path, mode="r", *args, **kwargs):
        if path == config_path and mode in {"w", "x"}:
            with original_open(path, "x", encoding="utf-8") as config_file:
                config_file.write("[project]\ntype = 'library'\n")
        return original_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", open_after_concurrent_creation)
    result = CliRunner().invoke(app, ["init", str(tmp_path)])

    assert result.exit_code == 2
    assert "already exists" in result.stderr
    assert config_path.read_text(encoding="utf-8") == "[project]\ntype = 'library'\n"


def test_project_type_detection_supports_python_and_react(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
    assert detect_project_type(tmp_path)[0] == "python"

    (tmp_path / "pyproject.toml").unlink()
    (tmp_path / "package.json").write_text(
        '{"dependencies": {"react": "18"}, "scripts": {"dev": "vite"}}',
        encoding="utf-8",
    )
    assert detect_project_type(tmp_path)[0] == "react"


def test_project_type_detection_identifies_cli_metadata(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname = 'demo'\n\n[project.scripts]\ndemo = 'demo:main'\n",
        encoding="utf-8",
    )

    assert detect_project_type(tmp_path)[0] == "python-cli"


def test_project_type_detection_identifies_node_cli_metadata(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        '{"name":"demo","bin":{"demo":"cli.js"}}',
        encoding="utf-8",
    )

    assert detect_project_type(tmp_path)[0] == "node-cli"


def test_non_object_package_json_does_not_abort_scan(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text("[]", encoding="utf-8")

    report = scan_project(tmp_path)

    assert detect_project_type(tmp_path) == ("node", ["package.json"])
    tests = next(check for check in report.checks if check.category == "Tests")
    assert tests.details["package_json_test_script"] is False


def test_ignoring_metadata_preserves_inferred_project_weighting(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project.scripts]\nexample = "example:main"\n', encoding="utf-8"
    )
    (tmp_path / ".foliolint.toml").write_text('[ignore]\nchecks = ["metadata"]', encoding="utf-8")

    report = scan_project(tmp_path)

    assert [check.max_points for check in report.checks if check.category in {"Media", "Demo"}] == [
        5,
        5,
    ]


def test_cli_output_writes_report_file(tmp_path: Path) -> None:
    runner = CliRunner()
    output_path = tmp_path / "reports" / "scan.md"

    result = runner.invoke(
        app,
        ["scan", str(tmp_path), "--format", "markdown", "--output", str(output_path)],
    )

    assert result.exit_code == 0
    assert "| Category | Status | Points | Notes |" not in result.stdout
    assert "Report written to" in result.stdout
    assert "# FolioLint Report" in output_path.read_text(encoding="utf-8")


def test_cli_json_output_is_stable(tmp_path: Path) -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["scan", str(tmp_path), "--format", "json"])

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert set(data) == {"score", "status", "checks", "recommendations"}
    assert isinstance(data["checks"], list)
    assert data["checks"][0]["category"] == "README"


def test_cli_no_score_hides_score_in_json(tmp_path: Path) -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["scan", str(tmp_path), "--format", "json", "--no-score"])

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert "score" not in data
    assert "status" not in data


def test_cli_no_score_hides_score_in_text(tmp_path: Path) -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["scan", str(tmp_path), "--no-score"])

    assert result.exit_code == 0
    assert "Score:" not in result.stdout
    assert "Status:" not in result.stdout


def test_cli_markdown_output(tmp_path: Path) -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["scan", str(tmp_path), "--format", "markdown"])

    assert result.exit_code == 0
    assert "# FolioLint Report" in result.stdout
    assert "| Category | Status | Points | Notes |" in result.stdout
    assert "README" in result.stdout


def test_cli_fail_under_exits_with_error(tmp_path: Path) -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["scan", str(tmp_path), "--fail-under", "75"])

    assert result.exit_code == 1
    assert "Score:" in result.stdout


def test_cli_fail_under_rejects_no_score(tmp_path: Path) -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["scan", str(tmp_path), "--no-score", "--fail-under", "75"])

    assert result.exit_code == 2
    assert "--fail-under cannot be used together with --no-score" in result.stderr


def test_cli_details_shows_check_details(tmp_path: Path) -> None:
    (tmp_path / "settings.py").write_text("PASS" + "WORD = 'example'\n", encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(app, ["scan", str(tmp_path), "--details"])

    assert result.exit_code == 0
    assert "Details" in result.stdout
    assert "settings.py:1" in result.stdout
