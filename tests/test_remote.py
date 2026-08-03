import json
import zipfile
from io import BytesIO
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

    def fake_download_zip(
        url: str,
        destination: Path,
        *,
        max_download_mb: int,
    ) -> None:
        del url
        del max_download_mb
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

    def fake_download_zip(
        url: str,
        destination: Path,
        *,
        max_download_mb: int,
    ) -> None:
        del max_download_mb
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

    def fake_download_zip(
        url: str,
        destination: Path,
        *,
        max_download_mb: int,
    ) -> None:
        del max_download_mb
        urls.append(url)
        destination.write_bytes(archive.read_bytes())

    monkeypatch.setattr(remote, "download_zip", fake_download_zip)

    with prepare_remote_repository(
        "https://github.com/AleksZyro/FolioLint",
        branch="develop",
    ) as repo:
        assert repo.branch == "develop"

    assert urls == ["https://github.com/AleksZyro/FolioLint/archive/refs/heads/develop.zip"]


def test_prepare_remote_repository_keeps_download_limit_error(monkeypatch) -> None:
    urls: list[str] = []

    def fake_download_zip(
        url: str,
        destination: Path,
        *,
        max_download_mb: int,
    ) -> None:
        del destination
        urls.append(url)
        raise remote.DownloadTooLargeError(
            f"FolioLint stopped the download because it is larger than {max_download_mb} MB."
        )

    monkeypatch.setattr(remote, "download_zip", fake_download_zip)

    try:
        with prepare_remote_repository(
            "https://github.com/AleksZyro/FolioLint",
            max_download_mb=3,
        ):
            raise AssertionError("Expected RemoteScanError")
    except RemoteScanError as error:
        assert "larger than 3 MB" in str(error)

    assert urls == ["https://github.com/AleksZyro/FolioLint/archive/refs/heads/main.zip"]


def test_download_zip_stops_when_content_length_is_too_large(tmp_path: Path, monkeypatch) -> None:
    response = _FakeResponse(b"small", content_length=2 * 1024 * 1024)
    monkeypatch.setattr(remote.urllib.request, "urlopen", lambda url, timeout: response)

    try:
        remote.download_zip(
            "https://example.test/repo.zip",
            tmp_path / "repo.zip",
            max_download_mb=1,
        )
    except RemoteScanError as error:
        assert "larger than 1 MB" in str(error)
    else:
        raise AssertionError("Expected RemoteScanError")


def test_download_zip_stops_while_streaming_large_response(tmp_path: Path, monkeypatch) -> None:
    response = _FakeResponse(b"x" * (2 * 1024 * 1024), content_length=None)
    monkeypatch.setattr(remote.urllib.request, "urlopen", lambda url, timeout: response)

    try:
        remote.download_zip(
            "https://example.test/repo.zip",
            tmp_path / "repo.zip",
            max_download_mb=1,
        )
    except RemoteScanError as error:
        assert "protects your disk space" in str(error)
    else:
        raise AssertionError("Expected RemoteScanError")


def test_scan_url_json_output(tmp_path: Path, monkeypatch) -> None:
    archive = _make_repo_zip(tmp_path, "FolioLint-main")

    def fake_download_zip(
        url: str,
        destination: Path,
        *,
        max_download_mb: int,
    ) -> None:
        del url
        del max_download_mb
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
    assert data["remote"]["source_url"] == "https://github.com/AleksZyro/FolioLint"
    assert data["remote"]["temporary_copy"] == "removed after scan"


def test_scan_url_invalid_url_returns_clear_error() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["scan-url", "https://example.com/OWNER/REPO"])

    assert result.exit_code == 2
    assert "https://github.com/OWNER/REPO" in result.stderr


def test_scan_url_fail_under(tmp_path: Path, monkeypatch) -> None:
    archive = _make_repo_zip(tmp_path, "FolioLint-main")

    def fake_download_zip(
        url: str,
        destination: Path,
        *,
        max_download_mb: int,
    ) -> None:
        del url
        del max_download_mb
        destination.write_bytes(archive.read_bytes())

    monkeypatch.setattr(remote, "download_zip", fake_download_zip)
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["scan-url", "https://github.com/AleksZyro/FolioLint", "--fail-under", "100"],
    )

    assert result.exit_code == 1
    assert "Score:" in result.stdout


def test_scan_url_passes_max_download_limit(tmp_path: Path, monkeypatch) -> None:
    archive = _make_repo_zip(tmp_path, "FolioLint-main")
    limits: list[int] = []

    def fake_download_zip(url: str, destination: Path, *, max_download_mb: int) -> None:
        del url
        limits.append(max_download_mb)
        destination.write_bytes(archive.read_bytes())

    monkeypatch.setattr(remote, "download_zip", fake_download_zip)
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "scan-url",
            "https://github.com/AleksZyro/FolioLint",
            "--max-download-mb",
            "7",
        ],
    )

    assert result.exit_code == 0
    assert limits == [7]


def test_scan_url_text_output_shows_remote_cleanup(tmp_path: Path, monkeypatch) -> None:
    archive = _make_repo_zip(tmp_path, "FolioLint-main")

    def fake_download_zip(url: str, destination: Path, *, max_download_mb: int) -> None:
        del url
        del max_download_mb
        destination.write_bytes(archive.read_bytes())

    monkeypatch.setattr(remote, "download_zip", fake_download_zip)
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["scan-url", "https://github.com/AleksZyro/FolioLint"],
    )

    assert result.exit_code == 0
    assert "Remote: https://github.com/AleksZyro/FolioLint" in result.stdout
    assert "Temporary copy: removed after scan" in result.stdout


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


class _FakeResponse:
    def __init__(self, body: bytes, *, content_length: int | None) -> None:
        self._stream = BytesIO(body)
        self.headers = {}
        if content_length is not None:
            self.headers["Content-Length"] = str(content_length)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self._stream.close()

    def read(self, size: int = -1) -> bytes:
        return self._stream.read(size)
