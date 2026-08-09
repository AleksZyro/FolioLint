import subprocess
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


def test_hygiene_check_ignores_gitignored_cache_dirs(tmp_path: Path) -> None:
    (tmp_path / ".gitignore").write_text(".pytest_cache/\n__pycache__/\n", encoding="utf-8")
    (tmp_path / ".pytest_cache").mkdir()
    cache = tmp_path / "src" / "__pycache__"
    cache.mkdir(parents=True)
    (cache / "module.pyc").write_bytes(b"cache")

    result = check_hygiene(tmp_path, ShowcaseConfig())

    assert result.status == "ok"
    assert result.details["generated_dirs"] == []
    assert ".pytest_cache" in result.details["ignored_local_paths"]
    assert "src/__pycache__" in result.details["ignored_local_paths"]


def test_hygiene_check_ignores_untracked_cache_in_git_repo(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / ".pytest_cache").mkdir()

    result = check_hygiene(tmp_path, ShowcaseConfig())

    assert result.status == "ok"
    assert result.details["uses_git_tracking"] is True
    assert ".pytest_cache" in result.details["ignored_local_paths"]


def test_hygiene_check_warns_for_tracked_generated_dir(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "bundle.js").write_text("console.log('demo')\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "dist/bundle.js"], check=True)

    result = check_hygiene(tmp_path, ShowcaseConfig())

    assert result.status == "warning"
    assert result.details["uses_git_tracking"] is True
    assert result.details["generated_dirs"] == ["dist"]


def test_secret_check_detects_obvious_risk_hint(tmp_path: Path) -> None:
    (tmp_path / "settings.py").write_text("API" + "_KEY = 'not-real'\n", encoding="utf-8")

    result = check_secrets(tmp_path, ShowcaseConfig())

    assert result.status == "warning"
    assert result.details["matches"][0]["pattern"] == "API_KEY"
    assert result.details["matches"][0]["line"] == "1"


def test_secret_check_detects_provider_prefixed_api_key(tmp_path: Path) -> None:
    (tmp_path / "settings.py").write_text("OPENAI_API" + "_KEY = 'not-real'\n", encoding="utf-8")

    result = check_secrets(tmp_path, ShowcaseConfig())

    assert result.status == "warning"
    assert result.details["matches"][0]["pattern"] == "OPENAI_API_KEY"
    assert result.details["matches"][0]["line"] == "1"


def test_secret_check_ignores_documented_pattern_names(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        "The tool can mention API" + "_KEY, SECRET and TO" + "KEN as examples.\n",
        encoding="utf-8",
    )

    result = check_secrets(tmp_path, ShowcaseConfig())

    assert result.status == "ok"
    assert result.details["matches"] == []


def test_secret_check_skips_generated_dependency_folders(tmp_path: Path) -> None:
    package = tmp_path / "node_modules" / "example"
    package.mkdir(parents=True)
    (package / "index.js").write_text("PASS" + "WORD = 'example'\n", encoding="utf-8")

    result = check_secrets(tmp_path, ShowcaseConfig())

    assert result.status == "ok"
    assert result.details["matches"] == []


def test_secret_check_ignores_github_actions_id_token_permission(tmp_path: Path) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "deploy.yml").write_text(
        """
name: Deploy
permissions:
  contents: read
  id-token: write
""",
        encoding="utf-8",
    )

    result = check_secrets(tmp_path, ShowcaseConfig())

    assert result.status == "ok"
    assert result.details["matches"] == []


def test_tests_check_ignores_empty_github_actions(tmp_path: Path) -> None:
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_app.py").write_text("def test_app():\n    assert True\n", encoding="utf-8")
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "tests.yml").write_text("name: tests\n", encoding="utf-8")

    result = check_tests(tmp_path, ShowcaseConfig())

    assert result.status == "ok"
    assert result.details["github_actions"] is False
    assert result.details["github_actions_files"] == [".github/workflows/tests.yml"]
    assert result.points == 10


def test_tests_check_detects_meaningful_github_actions(tmp_path: Path) -> None:
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_app.py").write_text("def test_app():\n    assert True\n", encoding="utf-8")
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yml").write_text(
        """
name: CI
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/setup-python@v5
      - run: python -m pytest
      - run: ruff check .
""",
        encoding="utf-8",
    )

    result = check_tests(tmp_path, ShowcaseConfig())

    assert result.status == "ok"
    assert result.details["github_actions"] is True
    assert result.details["github_actions_tools"] == ["pytest", "python", "ruff"]
    assert result.points == 13


def test_tests_check_detects_javascript_test_files(tmp_path: Path) -> None:
    src = tmp_path / "src" / "utils"
    src.mkdir(parents=True)
    (src / "grid.test.js").write_text("import { test } from 'vitest'\n", encoding="utf-8")
    (tmp_path / "package.json").write_text(
        '{"scripts":{"test":"vitest run"}}',
        encoding="utf-8",
    )
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yml").write_text(
        """
name: CI
jobs:
  test:
    steps:
      - run: npm test
""",
        encoding="utf-8",
    )

    result = check_tests(tmp_path, ShowcaseConfig())

    assert result.status == "ok"
    assert result.details["test_files"] == ["src/utils/grid.test.js"]
    assert result.points == 10


def _init_git_repo(path: Path) -> None:
    subprocess.run(["git", "-C", str(path), "init"], check=True, capture_output=True)
