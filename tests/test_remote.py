import json
import zipfile
from pathlib import Path

from typer.testing import CliRunner

from foliolint import remote
from foliolint.cli import app
from foliolint.remote import RemoteScanError, parse_github_repo_url, prepare_remote_repository


def test_parse_github_repo_url_accepts_simple_url() -> None:
    repo = parse_github_repo_url("https://github.com/AleksZyro/FolioLint/")

    assert repo.owner == "AleksZyro"
    assert repo.name == "FolioLint"
    assert repo.zip_url("main") == (
        "https://github.com/AleksZyro/FolioLint/archive/refs/heads/main.zip"
    )


def test_parse_github_repo_url_rejects_invalid_url() -> None:
    try:
        parse_github_repo_url("https://example.com/AleksZyro/FolioLint")
    except RemoteScanError as error:
        assert "https://github.com/OWNER/REPO" in str(error)
    else:
        raise AssertionError("Expected RemoteScanError")


def test_prepare_remote_repository_extracts_zip_and_cleans_temp(
    tmp_path: Path,
    monkeypatch,
) -> None:
    archive = _make_repo_zip(tmp_path, "FolioLint-main")
    seen_repo_path: Path | None = None

    def fake_download_zip(url: str, destination: Path) -> None:
        del url
        destination.write_bytes(archive.read_bytes())

    monkeypatch.setattr(remote, "download_zip", fake_download_zip)

    with prepare_remote_repository("https://github.com/AleksZyro/FolioLint") as repo:
        seen_repo_path = repo.path
        assert repo.branch == "main"
        assert (repo.path / "README.md").exists()

    assert seen_repo_path is not None
    assert not seen_repo_path.exists()


def test_prepare_remote_repository_falls_back_to_master(tmp_path: Path, monkeypatch) -> None:
    archive = _make_repo_zip(tmp_path, "FolioLint-master")
    urls: list[str] = []

    def fake_download_zip(url: str, destination: Path) -> None:
        urls.append(url)
        if url.endswith("/main.zip"):
            raise RemoteScanError("main failed")
        destination.write_bytes(archive.read_bytes())

    monkeypatch.setattr(remote, "download_zip", fake_download_zip)

    with prepare_remote_repository("https://github.com/AleksZyro/FolioLint") as repo:
        assert repo.branch == "master"

    assert urls == [
        "https://github.com/AleksZyro/FolioLint/archive/refs/heads/main.zip",
        "https://github.com/AleksZyro/FolioLint/archive/refs/heads/master.zip",
    ]


def test_prepare_remote_repository_uses_explicit_branch(tmp_path: Path, monkeypatch) -> None:
    archive = _make_repo_zip(tmp_path, "FolioLint-develop")
    urls: list[str] = []

    def fake_download_zip(url: str, destination: Path) -> None:
        urls.append(url)
        destination.write_bytes(archive.read_bytes())

    monkeypatch.setattr(remote, "download_zip", fake_download_zip)

    with prepare_remote_repository(
        "https://github.com/AleksZyro/FolioLint",
        branch="develop",
    ) as repo:
        assert repo.branch == "develop"

    assert urls == ["https://github.com/AleksZyro/FolioLint/archive/refs/heads/develop.zip"]


def test_scan_url_json_output(tmp_path: Path, monkeypatch) -> None:
    archive = _make_repo_zip(tmp_path, "FolioLint-main")

    def fake_download_zip(url: str, destination: Path) -> None:
        del url
        destination.write_bytes(archive.read_bytes())

    monkeypatch.setattr(remote, "download_zip", fake_download_zip)
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["scan-url", "https://github.com/AleksZyro/FolioLint", "--format", "json"],
    )

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["checks"][0]["category"] == "README"
    assert "score" in data


def test_scan_url_invalid_url_returns_clear_error() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["scan-url", "https://example.com/OWNER/REPO"])

    assert result.exit_code == 2
    assert "https://github.com/OWNER/REPO" in result.stderr


def test_scan_url_fail_under(tmp_path: Path, monkeypatch) -> None:
    archive = _make_repo_zip(tmp_path, "FolioLint-main")

    def fake_download_zip(url: str, destination: Path) -> None:
        del url
        destination.write_bytes(archive.read_bytes())

    monkeypatch.setattr(remote, "download_zip", fake_download_zip)
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["scan-url", "https://github.com/AleksZyro/FolioLint", "--fail-under", "100"],
    )

    assert result.exit_code == 1
    assert "Score:" in result.stdout


def _make_repo_zip(tmp_path: Path, root_name: str) -> Path:
    archive_path = tmp_path / f"{root_name}.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr(
            f"{root_name}/README.md",
            """
# Example

## Installation
```bash
pip install -e .
```

## Usage
```bash
python -m example
```

## Tests
```bash
pytest
```

## Limitations
Prototype.
""",
        )
    return archive_path
