from __future__ import annotations

import tempfile
import urllib.error
import urllib.request
import zipfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

DEFAULT_MAX_DOWNLOAD_MB = 50
BYTES_PER_MB = 1024 * 1024


class RemoteScanError(RuntimeError):
    """Raised when a remote repository cannot be prepared for scanning."""


class DownloadTooLargeError(RemoteScanError):
    """Raised when a repository ZIP exceeds the configured download limit."""


@dataclass(frozen=True)
class GitHubRepo:
    owner: str
    name: str

    def zip_url(self, branch: str) -> str:
        return f"https://github.com/{self.owner}/{self.name}/archive/refs/heads/{branch}.zip"


@dataclass(frozen=True)
class RemoteRepository:
    path: Path
    branch: str
    url: str


def parse_github_repo_url(url: str) -> GitHubRepo:
    parsed = urlparse(url.strip())
    parts = [part for part in parsed.path.strip("/").split("/") if part]
    if (
        parsed.scheme != "https"
        or parsed.netloc.lower() != "github.com"
        or parsed.query
        or parsed.fragment
        or len(parts) != 2
    ):
        raise RemoteScanError(
            "FolioLint only supports public GitHub repository URLs like "
            "https://github.com/OWNER/REPO."
        )
    owner, repo = parts
    if not owner or not repo or repo.endswith(".git"):
        raise RemoteScanError(
            "FolioLint only supports public GitHub repository URLs like "
            "https://github.com/OWNER/REPO."
        )
    return GitHubRepo(owner=owner, name=repo)


@contextmanager
def prepare_remote_repository(
    url: str,
    *,
    branch: str | None = None,
    max_download_mb: int = DEFAULT_MAX_DOWNLOAD_MB,
) -> Iterator[RemoteRepository]:
    repo = parse_github_repo_url(url)
    branches = [branch] if branch else ["main", "master"]
    with tempfile.TemporaryDirectory(prefix="foliolint-remote-") as temp_dir:
        temp_path = Path(temp_dir)
        last_error: RemoteScanError | None = None
        for candidate_branch in branches:
            zip_path = temp_path / f"{repo.owner}-{repo.name}-{candidate_branch}.zip"
            try:
                download_zip(
                    repo.zip_url(candidate_branch),
                    zip_path,
                    max_download_mb=max_download_mb,
                )
                extract_zip(zip_path, temp_path)
                repo_path = find_extracted_repo(temp_path, zip_path)
            except DownloadTooLargeError:
                raise
            except RemoteScanError as error:
                last_error = error
                continue
            yield RemoteRepository(
                path=repo_path,
                branch=candidate_branch,
                url=repo.zip_url(candidate_branch),
            )
            return

    if branch:
        raise RemoteScanError(
            "FolioLint could not download this repository. Check that the repository is "
            "public and that the branch name is correct."
        ) from last_error
    raise RemoteScanError(
        "FolioLint could not download this repository from the main or master branch. "
        "Check that the repository is public, or pass the branch name with --branch."
    ) from last_error


def download_zip(
    url: str,
    destination: Path,
    *,
    max_download_mb: int = DEFAULT_MAX_DOWNLOAD_MB,
) -> None:
    max_bytes = max_download_mb * BYTES_PER_MB
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            content_length = response.headers.get("Content-Length")
            if _content_length_exceeds_limit(content_length, max_bytes):
                raise DownloadTooLargeError(_download_limit_message(max_download_mb))
            with destination.open("wb") as file:
                copied = 0
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    copied += len(chunk)
                    if copied > max_bytes:
                        raise DownloadTooLargeError(_download_limit_message(max_download_mb))
                    file.write(chunk)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            raise RemoteScanError(
                "FolioLint could not find that repository or branch. Check that the "
                "repository is public and that the branch name is correct."
            ) from error
        raise RemoteScanError(
            "FolioLint could not download this repository. Please try again later."
        ) from error
    except (OSError, urllib.error.URLError) as error:
        raise RemoteScanError(
            "FolioLint could not download this repository. Check your internet connection "
            "and the repository URL."
        ) from error


def extract_zip(zip_path: Path, destination: Path) -> None:
    try:
        with zipfile.ZipFile(zip_path) as archive:
            archive.extractall(destination)
    except (OSError, zipfile.BadZipFile) as error:
        raise RemoteScanError(
            "FolioLint downloaded the repository ZIP, but could not unpack it."
        ) from error


def find_extracted_repo(temp_path: Path, zip_path: Path) -> Path:
    directories = [
        path for path in temp_path.iterdir() if path.is_dir() and path.name != zip_path.stem
    ]
    if len(directories) == 1:
        return directories[0]
    if directories:
        return sorted(directories, key=lambda path: path.name)[0]
    raise RemoteScanError("FolioLint could not find the downloaded repository folder.")


def _download_limit_message(max_download_mb: int) -> str:
    return (
        f"FolioLint stopped the download because it is larger than {max_download_mb} MB. "
        "This protects your disk space. Use --max-download-mb to allow a larger download."
    )


def _content_length_exceeds_limit(content_length: str | None, max_bytes: int) -> bool:
    if not content_length:
        return False
    try:
        return int(content_length) > max_bytes
    except ValueError:
        return False
