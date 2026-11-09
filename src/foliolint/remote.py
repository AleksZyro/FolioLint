from __future__ import annotations

import re
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
DEFAULT_MAX_EXTRACTED_MB = 250
DEFAULT_MAX_ARCHIVE_FILES = 5000
BYTES_PER_MB = 1024 * 1024


class RemoteScanError(RuntimeError):
    """Raised when a remote repository cannot be prepared for scanning."""


class DownloadTooLargeError(RemoteScanError):
    """Raised when a repository ZIP exceeds the configured download limit."""


class ArchiveTooLargeError(RemoteScanError):
    """Raised when a repository ZIP expands beyond configured extraction limits."""


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
        or parts[-1].endswith(".git")
    ):
        raise RemoteScanError(
            "FolioLint only supports public GitHub repository URLs like "
            "https://github.com/OWNER/REPO."
        )
    owner, repo = parts
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
    last_error: RemoteScanError | None = None
    for branch_index, candidate_branch in enumerate(branches):
        _validate_branch_name(candidate_branch)
        zip_url = repo.zip_url(candidate_branch)
        with tempfile.TemporaryDirectory(prefix="foliolint-remote-") as temp_dir:
            temp_path = Path(temp_dir)
            zip_path = temp_path / f"archive-{branch_index}.zip"
            try:
                download_zip(
                    zip_url,
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
                url=zip_url,
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


def _validate_branch_name(branch: str) -> None:
    if (
        not branch
        or branch == "."
        or "//" in branch
        or ".." in branch
        or branch.startswith("/")
        or branch.endswith("/")
        or not re.fullmatch(r"[A-Za-z0-9._/-]+", branch)
    ):
        raise RemoteScanError(
            "FolioLint could not use that branch name. Use a normal GitHub branch name "
            "such as main or feature/demo."
        )


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
                while chunk := response.read(BYTES_PER_MB):
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
    except OSError as error:
        raise RemoteScanError(
            "FolioLint could not download this repository. Check your internet connection "
            "and the repository URL."
        ) from error


def extract_zip(
    zip_path: Path,
    destination: Path,
    *,
    max_extracted_mb: int = DEFAULT_MAX_EXTRACTED_MB,
    max_files: int = DEFAULT_MAX_ARCHIVE_FILES,
) -> None:
    try:
        with zipfile.ZipFile(zip_path) as archive:
            root = destination.resolve()
            _validate_zip_members(
                archive,
                root,
                max_extracted_mb=max_extracted_mb,
                max_files=max_files,
            )
            archive.extractall(root, members=archive.infolist())
    except (OSError, zipfile.BadZipFile) as error:
        raise RemoteScanError(
            "FolioLint downloaded the repository ZIP, but could not unpack it."
        ) from error


def find_extracted_repo(temp_path: Path, zip_path: Path) -> Path:
    directories = (
        path for path in temp_path.iterdir() if path.is_dir() and path.name != zip_path.stem
    )
    directory = min(directories, key=lambda path: path.name, default=None)
    if directory is not None:
        return directory
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


def _validate_zip_members(
    archive: zipfile.ZipFile,
    destination_root: Path,
    *,
    max_extracted_mb: int,
    max_files: int,
) -> None:
    members = archive.infolist()
    file_members = [member for member in members if not member.is_dir()]
    if len(file_members) > max_files:
        raise ArchiveTooLargeError(
            f"FolioLint stopped the ZIP because it contains more than {max_files} files."
        )

    max_extracted_bytes = max_extracted_mb * BYTES_PER_MB
    extracted_bytes = sum(member.file_size for member in file_members)
    if extracted_bytes > max_extracted_bytes:
        raise ArchiveTooLargeError(
            f"FolioLint stopped the ZIP because it expands beyond {max_extracted_mb} MB."
        )

    for member in members:
        target = (destination_root / member.filename).resolve()
        if not target.is_relative_to(destination_root):
            raise RemoteScanError(
                "FolioLint stopped the ZIP because it contains an unsafe file path."
            )
