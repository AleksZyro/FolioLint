from pathlib import Path

from foliolint.checks import check_readme
from foliolint.cli import app
from foliolint.config import ShowcaseConfig
from typer.testing import CliRunner


def test_readme_check_empty_project(tmp_path: Path) -> None:
    result = check_readme(tmp_path, ShowcaseConfig())

    assert result.status == "warning"
    assert result.points == 0
    assert "README.md" in result.message


def test_readme_check_good_python_project(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
# Example

## About
This project demonstrates a local CLI workflow for portfolio review.

## Installation
Run pip install -e .

## Usage
Run python -m example or use the quick start command.

## Tests
Run pytest.

## Status
Prototype with known limitations.

## Demo
See docs/assets/screenshot.png.
""",
        encoding="utf-8",
    )

    result = check_readme(tmp_path, ShowcaseConfig())

    assert result.status == "ok"
    assert result.points == 25


def test_readme_check_detects_headings_and_code_blocks(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
# Example

## Overview
Small local tool.

## Installation
```bash
pip install -e .
```

## Quick Start
```bash
python -m example
```

## Tests
```bash
pytest
```

## Limitations
Prototype.

## Demo
![preview](docs/assets/screenshot.png)
""",
        encoding="utf-8",
    )

    result = check_readme(tmp_path, ShowcaseConfig())

    assert result.status == "ok"
    assert result.points == 25
    assert "heading 'installation'" in result.details["matches"]["setup"]
    assert "code command 'pytest'" in result.details["matches"]["tests"]
    assert "Matches:" in result.explanation


def test_cli_explain_shows_points(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Example\n\nUsage: run pytest.\n", encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(app, ["scan", str(tmp_path), "--explain"])

    assert result.exit_code == 0
    assert "Explanation" in result.stdout
    assert "README" in result.stdout
