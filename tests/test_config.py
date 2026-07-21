import json
from pathlib import Path

from typer.testing import CliRunner

from foliolint.cli import app
from foliolint.config import load_config
from foliolint.scanner import scan_project


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
status = "prototype"
""",
        encoding="utf-8",
    )

    config = load_config(tmp_path)

    assert config.ignore.paths == ["dist", "docs/assets/large-demo.mp4"]
    assert config.ignore.checks == ["demo-link"]
    assert config.thresholds.large_file_mb == 10
    assert config.project.type == "local-app"
    assert config.project.status == "prototype"


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
