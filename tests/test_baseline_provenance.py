from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from foliolint.baseline import compare_baseline, load_baseline, save_baseline
from foliolint.cli import app
from foliolint.models import ScanReport


def test_saved_local_baseline_records_schema_and_normalized_origin(tmp_path: Path) -> None:
    repository = _git_repository(tmp_path / "repository", "git@github.com:Owner/Example.git")
    baseline_path = tmp_path / "baseline.json"

    save_baseline(_report(repository), baseline_path)

    baseline = load_baseline(baseline_path)
    assert baseline["schema_version"] == 2
    assert baseline["provenance"] == {"origin": "https://github.com/owner/example"}


def test_matching_local_git_repositories_can_be_compared(tmp_path: Path) -> None:
    first = _git_repository(tmp_path / "first", "https://github.com/owner/example.git")
    second = _git_repository(tmp_path / "second", "git@github.com:owner/example.git")
    baseline_path = tmp_path / "baseline.json"
    save_baseline(_report(first), baseline_path)

    comparison = compare_baseline(_report(second), load_baseline(baseline_path))

    assert comparison["identity_status"] == "matched"


def test_mismatched_local_git_repositories_are_refused_by_cli(tmp_path: Path) -> None:
    first = _git_repository(tmp_path / "first", "https://github.com/owner/first.git")
    second = _git_repository(tmp_path / "second", "https://github.com/owner/second.git")
    baseline_path = tmp_path / "baseline.json"
    save_baseline(_report(first), baseline_path)

    result = CliRunner().invoke(
        app,
        ["scan", str(second), "--compare-baseline", str(baseline_path)],
    )

    assert result.exit_code == 2
    assert "different repository" in result.stderr


@pytest.mark.parametrize(
    ("baseline_provenance", "current_provenance"),
    [
        (
            {"source_url": "https://github.com/owner/example", "branch": "main"},
            {"source_url": "https://github.com/other/example", "branch": "main"},
        ),
        (
            {"source_url": "https://github.com/owner/example", "branch": "main"},
            {"source_url": "https://github.com/owner/example", "branch": "develop"},
        ),
    ],
)
def test_remote_url_or_branch_mismatch_is_refused(
    baseline_provenance: dict[str, str], current_provenance: dict[str, str]
) -> None:
    baseline = {"score": 50, "checks": [], "schema_version": 2, "provenance": baseline_provenance}

    with pytest.raises(ValueError, match="different repository"):
        compare_baseline(_report(Path("."), remote=current_provenance), baseline)


def test_legacy_baseline_remains_comparable_but_is_unverified() -> None:
    baseline = {"score": 50, "checks": []}

    comparison = compare_baseline(_report(Path(".")), baseline)

    assert comparison["identity_status"] == "legacy_unverified"


def test_local_folder_without_git_metadata_is_not_claimed_as_matched(tmp_path: Path) -> None:
    baseline_path = tmp_path / "baseline.json"
    save_baseline(_report(tmp_path), baseline_path)

    comparison = compare_baseline(_report(tmp_path), load_baseline(baseline_path))

    assert "provenance" not in load_baseline(baseline_path)
    assert comparison["identity_status"] == "unverified"


def _report(path: Path, *, remote: dict[str, str] | None = None) -> ScanReport:
    return ScanReport(
        path=str(path),
        checks=[],
        recommendations=[],
        score=50,
        status="ready",
        remote=remote,
    )


def _git_repository(path: Path, origin: str) -> Path:
    path.mkdir()
    _git(path, "init")
    _git(path, "remote", "add", "origin", origin)
    return path


def _git(path: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=path, check=True, capture_output=True, text=True)
