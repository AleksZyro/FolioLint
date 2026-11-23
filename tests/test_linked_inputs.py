from pathlib import Path

import pytest

from foliolint.config import CONFIG_FILE, ConfigError, load_config
from foliolint.scanner import scan_project


def link(path: Path, target: Path) -> None:
    try:
        path.symlink_to(target, target_is_directory=target.is_dir())
    except OSError as error:
        if getattr(error, "winerror", None) == 1314:
            pytest.skip("Windows symlink privilege unavailable")
        raise


def test_scan_ignores_linked_readme_and_workflows(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    readme = tmp_path / "notes.md"
    readme.write_text("# Setup", encoding="utf-8")
    link(root / "README.md", readme)
    workflows = tmp_path / "ci"
    workflows.mkdir()
    (workflows / "test.yml").write_text("run: pytest", encoding="utf-8")
    (root / ".github").mkdir()
    link(root / ".github" / "workflows", workflows)
    checks = {check.category: check for check in scan_project(root).checks}
    assert not checks["README"].details["exists"]
    assert not checks["Tests"].details["github_actions_files"]


def test_config_requires_a_regular_file(tmp_path):
    (tmp_path / CONFIG_FILE).mkdir()
    with pytest.raises(ConfigError, match="regular configuration file"):
        load_config(tmp_path)
