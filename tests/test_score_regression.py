"""Golden scores recorded against the original monolithic check engine."""

from pathlib import Path

import pytest

from foliolint.scanner import scan_project


@pytest.fixture
def showcase(tmp_path: Path) -> Path:
    (tmp_path / "README.md").write_text(
        "# Example\n\n## About\nThis project demonstrates a local CLI workflow.\n"
        "## Installation\npip install -e .\n## Usage\npython -m example\n"
        "## Tests\npytest\n## Status\nPrototype with limitations.\n"
        "## Demo\n![preview](docs/assets/screenshot.png)\n",
        encoding="utf-8",
    )
    (tmp_path / "LICENSE").write_text("MIT", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_example.py").write_text("", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "example"\n[project.scripts]\nexample = "example:main"\n',
        encoding="utf-8",
    )
    return tmp_path


@pytest.mark.parametrize("strict, expected", [(False, 25), (True, 25)])
def test_empty_score_is_unchanged(tmp_path: Path, strict: bool, expected: int) -> None:
    report = scan_project(tmp_path, strict=strict)
    assert report.score == expected
    assert [(c.points, c.max_points) for c in report.checks] == [
        (0, 25),
        (0, 10),
        (0, 15),
        (0, 10),
        (0, 10),
        (15, 15),
        (10, 10),
        (0, 5),
    ]


@pytest.mark.parametrize(
    "project_type, strict, ignored, expected",
    [
        (None, False, [], 91),
        (None, True, [], 88),
        ("web-app", False, [], 92),
        ("library", False, [], 91),
        ("cli", True, ["demo-link"], 87),
        ("web-app", False, ["tests"], 96),
    ],
)
def test_showcase_score_is_unchanged(showcase, project_type, strict, ignored, expected) -> None:
    import json

    config = "[ignore]\nchecks = " + json.dumps(ignored) + "\n"
    if project_type:
        config += f'[project]\ntype = "{project_type}"\n'
    (showcase / ".foliolint.toml").write_text(config, encoding="utf-8")
    assert scan_project(showcase, strict=strict).score == expected
