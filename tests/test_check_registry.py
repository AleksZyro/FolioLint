import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from foliolint.check_metadata import CHECK_METADATA, MEDIA_LIGHT_PROJECT_TYPES
from foliolint.checks import CHECK_REGISTRY, run_checks
from foliolint.cli import app
from foliolint.config import IgnoreConfig, ShowcaseConfig
from foliolint.scoring import apply_project_type


def test_registry_retains_order_identities_and_maxima(tmp_path: Path) -> None:
    assert [entry.metadata for entry in CHECK_REGISTRY] == list(CHECK_METADATA)
    assert [entry.metadata.id for entry in CHECK_REGISTRY] == [
        "readme",
        "license",
        "tests",
        "media",
        "demo-link",
        "hygiene",
        "secrets",
        "metadata",
    ]
    assert len({entry.metadata.category for entry in CHECK_REGISTRY}) == 8
    assert sum(entry.metadata.max_points for entry in CHECK_REGISTRY) == 100
    for entry in CHECK_REGISTRY:
        result = entry.run(tmp_path, ShowcaseConfig())
        assert result.category == entry.metadata.category
        assert result.max_points == entry.metadata.max_points
        assert entry.metadata.description
        assert entry.metadata.ignorable


@pytest.mark.parametrize("entry", CHECK_REGISTRY, ids=lambda entry: entry.metadata.id)
def test_each_registered_check_can_be_ignored(tmp_path: Path, entry) -> None:
    config = ShowcaseConfig(ignore=IgnoreConfig(checks=[entry.metadata.id]))
    results = run_checks(tmp_path, config)
    result = next(result for result in results if result.category == entry.metadata.category)
    assert result.status == "ignored"
    assert result.points == result.max_points == 0
    assert result.recommendations == []
    assert sum(check.status == "ignored" for check in results) == 1


@pytest.mark.parametrize("project_type", sorted(MEDIA_LIGHT_PROJECT_TYPES))
def test_project_type_caps_match_metadata(tmp_path: Path, project_type: str) -> None:
    original = run_checks(tmp_path, ShowcaseConfig())
    adjusted = apply_project_type(original, f" {project_type.upper()} ")
    for entry, before, after in zip(CHECK_REGISTRY, original, adjusted, strict=True):
        cap = entry.metadata.project_type_max_points.get(project_type)
        assert after.max_points == (cap if cap is not None else before.max_points)


def test_ignored_check_stays_unscored_after_type_adjustment(tmp_path: Path) -> None:
    checks = run_checks(tmp_path, ShowcaseConfig(ignore=IgnoreConfig(checks=["media"])))
    adjusted = apply_project_type(checks, "cli")
    assert adjusted[3].status == "ignored"
    assert adjusted[3].points == adjusted[3].max_points == 0


def test_list_checks_text_and_json() -> None:
    runner = CliRunner()
    text = runner.invoke(app, ["list-checks"], terminal_width=140)
    assert text.exit_code == 0
    assert "demo-link" in text.stdout
    assert "Scored (max)" in text.stdout
    result = runner.invoke(app, ["list-checks", "--format", "json"])
    assert result.exit_code == 0
    assert json.loads(result.stdout) == [entry.metadata.to_dict() for entry in CHECK_REGISTRY]


def test_list_checks_rejects_report_only_format() -> None:
    assert CliRunner().invoke(app, ["list-checks", "--format", "html"]).exit_code == 2
