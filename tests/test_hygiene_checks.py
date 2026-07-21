from pathlib import Path

from foliolint.checks import check_hygiene, check_secrets, check_tests
from foliolint.config import ShowcaseConfig


def test_hygiene_check_detects_env_file(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("TO" + "KEN=abc\n", encoding="utf-8")

    result = check_hygiene(tmp_path, ShowcaseConfig())

    assert result.status == "warning"
    assert ".env" in result.details["env_files"]


def test_hygiene_check_detects_large_file(tmp_path: Path) -> None:
    large = tmp_path / "large.bin"
    large.write_bytes(b"0" * (6 * 1024 * 1024))

    result = check_hygiene(tmp_path, ShowcaseConfig())

    assert result.status == "warning"
    assert "large.bin" in result.details["large_files"]


def test_secret_check_detects_obvious_risk_hint(tmp_path: Path) -> None:
    (tmp_path / "settings.py").write_text("API" + "_KEY = 'not-real'\n", encoding="utf-8")

    result = check_secrets(tmp_path, ShowcaseConfig())

    assert result.status == "warning"
    assert result.details["matches"][0]["pattern"] == "API_KEY"


def test_secret_check_ignores_documented_pattern_names(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        "The tool can mention API" + "_KEY, SECRET and TO" + "KEN as examples.\n",
        encoding="utf-8",
    )

    result = check_secrets(tmp_path, ShowcaseConfig())

    assert result.status == "ok"
    assert result.details["matches"] == []


def test_tests_check_detects_github_actions(tmp_path: Path) -> None:
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_app.py").write_text("def test_app():\n    assert True\n", encoding="utf-8")
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "tests.yml").write_text("name: tests\n", encoding="utf-8")

    result = check_tests(tmp_path, ShowcaseConfig())

    assert result.status == "ok"
    assert result.details["github_actions"] is True
    assert result.points == 13
