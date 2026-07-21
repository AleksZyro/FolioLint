from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Iterable
from pathlib import Path

from foliolint.config import ShowcaseConfig
from foliolint.models import CheckResult

README_CHECK_ID = "readme"
LICENSE_CHECK_ID = "license"
TESTS_CHECK_ID = "tests"
MEDIA_CHECK_ID = "media"
DEMO_CHECK_ID = "demo-link"
HYGIENE_CHECK_ID = "hygiene"
SECRETS_CHECK_ID = "secrets"
METADATA_CHECK_ID = "metadata"

GENERATED_DIRS = {"dist", "build", "_site", "node_modules", "__pycache__", ".pytest_cache"}
SECRET_SCAN_SKIP_DIRS = GENERATED_DIRS | {".ruff_cache", ".venv", "venv", "site-packages"}
MEDIA_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".mp4", ".webm"}
MEDIA_DIRS = {"docs/assets", "assets", "public"}
TEXT_EXTENSIONS = {
    ".cfg",
    ".css",
    ".env",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".jsx",
    ".md",
    ".py",
    ".sh",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}
SECRET_PATTERNS = [
    "API" + "_KEY",
    "SECRET",
    "TOKEN",
    "PASSWORD",
    "PRIVATE" + "_KEY",
    "BEGIN " + "RSA PRIVATE KEY",
]
SECRET_ASSIGNMENT_RE = re.compile(
    r"\b(API" + r"_KEY|SECRET|TOKEN|PASSWORD|PRIVATE" + r"_KEY)\b\s*[:=]",
    re.IGNORECASE,
)
WORKFLOW_HINTS = {
    "pytest": ["pytest"],
    "ruff": ["ruff check", "ruff format", "ruff"],
    "python": ["python-version", "setup-python", "python -m", "python"],
    "npm_test": ["npm test", "npm run test"],
}
README_HEADINGS = {
    "purpose": ["about", "overview", "description", "purpose", "what is", "ziel", "zweck"],
    "setup": ["installation", "install", "setup", "requirements"],
    "usage": ["usage", "quick start", "getting started", "run", "start", "nutzung"],
    "tests": ["tests", "testing", "test"],
    "limitations": ["status", "limitations", "limits", "roadmap", "grenzen"],
    "screenshot_or_demo": ["demo", "screenshot", "screenshots", "preview"],
}
README_COMMANDS = {
    "setup": ["pip install", "npm install", "python -m venv"],
    "usage": ["python -m", "npm run dev", "npm start", "foliolint scan"],
    "tests": ["pytest", "python -m pytest", "npm test", "npm run test"],
}


def run_checks(path: Path, config: ShowcaseConfig) -> list[CheckResult]:
    checks = [
        (README_CHECK_ID, check_readme),
        (LICENSE_CHECK_ID, check_license),
        (TESTS_CHECK_ID, check_tests),
        (MEDIA_CHECK_ID, check_media),
        (DEMO_CHECK_ID, check_demo),
        (HYGIENE_CHECK_ID, check_hygiene),
        (SECRETS_CHECK_ID, check_secrets),
        (METADATA_CHECK_ID, check_metadata),
    ]
    results: list[CheckResult] = []
    ignored = set(config.ignore.checks)
    for check_id, check_func in checks:
        if check_id in ignored:
            results.append(
                CheckResult(
                    category=_category_for_id(check_id),
                    status="ignored",
                    message="Check ignored by configuration.",
                    points=0,
                    max_points=0,
                    explanation=f"The check id '{check_id}' is listed in .foliolint.toml.",
                )
            )
            continue
        results.append(check_func(path, config))
    return results


def check_readme(path: Path, config: ShowcaseConfig) -> CheckResult:
    del config
    readme = path / "README.md"
    if not readme.exists():
        return CheckResult(
            category="README",
            status="warning",
            message="No README.md file found.",
            points=0,
            max_points=25,
            details={"exists": False},
            explanation="README gets 0/25 because README.md is missing.",
            recommendations=["Add a README.md with purpose, setup, usage and current limits."],
        )

    text = _read_text(readme)
    lowered = text.lower()
    evidence = _readme_evidence(text)
    purpose_keywords = [
        "purpose",
        "what is",
        "about",
        "overview",
        "description",
        "ziel",
        "zweck",
        "projekt",
    ]
    setup_keywords = [
        "setup",
        "install",
        "installation",
        "requirements",
        "pip install",
        "npm install",
        "venv",
    ]
    usage_keywords = [
        "usage",
        "quick start",
        "getting started",
        "run",
        "start",
        "nutzung",
        "benutzung",
    ]
    limitation_keywords = [
        "status",
        "limitations",
        "limits",
        "grenzen",
        "roadmap",
        "prototype",
        "wip",
    ]
    media_keywords = [
        "screenshot",
        "demo",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".mp4",
        ".webm",
        "![",
    ]
    found = {
        "exists": True,
        "purpose": bool(evidence["purpose"])
        or _has_any(lowered, purpose_keywords)
        or len(text.strip()) >= 120,
        "setup": bool(evidence["setup"]) or _has_any(lowered, setup_keywords),
        "usage": bool(evidence["usage"]) or _has_any(lowered, usage_keywords),
        "tests": bool(evidence["tests"])
        or _has_any(lowered, ["test", "pytest", "unittest", "npm test", "coverage"]),
        "limitations": bool(evidence["limitations"]) or _has_any(lowered, limitation_keywords),
        "screenshot_or_demo": bool(evidence["screenshot_or_demo"])
        or _has_any(lowered, media_keywords),
    }
    for key, value in found.items():
        if value and key != "exists" and not evidence[key]:
            evidence[key].append("keyword or content heuristic")
    point_rules = {
        "exists": 5,
        "purpose": 4,
        "setup": 4,
        "usage": 4,
        "tests": 3,
        "limitations": 3,
        "screenshot_or_demo": 2,
    }
    points = sum(value for key, value in point_rules.items() if found[key])
    missing = [key for key in point_rules if not found[key]]
    status = "ok" if points >= 18 else "warning"
    message = _readme_message(found)
    recommendations = []
    if missing:
        recommendations.append(f"Improve README.md: add {', '.join(missing)}.")
    return CheckResult(
        category="README",
        status=status,
        message=message,
        points=points,
        max_points=25,
        details={**found, "matches": evidence},
        explanation=_readme_explanation(points, evidence),
        recommendations=recommendations,
    )


def check_license(path: Path, config: ShowcaseConfig) -> CheckResult:
    del config
    names = {child.name.upper() for child in path.iterdir() if child.is_file()}
    found = any(name in names for name in {"LICENSE", "LICENCE", "COPYING"})
    if found:
        return CheckResult(
            category="License",
            status="ok",
            message="License file found.",
            points=10,
            max_points=10,
            details={"found": True},
            explanation="License gets 10/10 because LICENSE, LICENCE or COPYING exists.",
        )
    return CheckResult(
        category="License",
        status="warning",
        message="No LICENSE, LICENCE or COPYING file found.",
        points=0,
        max_points=10,
        details={"found": False},
        explanation="License gets 0/10 because no license file was found.",
        recommendations=["Add or document the license decision before sharing publicly."],
    )


def check_tests(path: Path, config: ShowcaseConfig) -> CheckResult:
    files = list(_iter_files(path, config))
    has_tests_dir = (path / "tests").is_dir() and not _is_ignored(path / "tests", path, config)
    test_files = []
    for file in files:
        is_test_file = (file.name.startswith("test_") and file.suffix == ".py") or (
            file.name.endswith("_test.py")
        )
        if is_test_file:
            test_files.append(file)
    package_test = _package_json_has_test_script(path / "package.json")
    github_actions_details = _github_actions_details(path)
    github_actions = github_actions_details["has_meaningful_checks"]
    points = 0
    if has_tests_dir:
        points += 5
    if test_files:
        points += 5
    if package_test:
        points += 2
    if github_actions:
        points += 3
    details = {
        "tests_dir": has_tests_dir,
        "test_files": [file.relative_to(path).as_posix() for file in test_files[:10]],
        "package_json_test_script": package_test,
        "github_actions": github_actions,
        "github_actions_files": github_actions_details["files"],
        "github_actions_tools": github_actions_details["tools"],
    }
    status = "ok" if points >= 8 else "warning"
    message = "Test setup detected." if points >= 8 else "No clear test setup detected."
    recommendations = []
    if not test_files:
        recommendations.append("Add test_*.py or *_test.py files under tests/.")
    if not github_actions:
        recommendations.append(
            "Add a GitHub Actions workflow that runs pytest, ruff or another test command."
        )
    return CheckResult(
        category="Tests",
        status=status,
        message=message,
        points=points,
        max_points=15,
        details=details,
        explanation=(
            f"Tests gets {points}/15 from tests folder, test files, "
            "package test script and GitHub Actions."
        ),
        recommendations=recommendations,
    )


def check_media(path: Path, config: ShowcaseConfig) -> CheckResult:
    media_files = []
    for file in _iter_files(path, config):
        rel = file.relative_to(path).as_posix()
        in_media_dir = any(rel.startswith(f"{media_dir}/") for media_dir in MEDIA_DIRS)
        if in_media_dir and file.suffix.lower() in MEDIA_EXTENSIONS:
            media_files.append(rel)

    readme_text = _read_text(path / "README.md").lower()
    readme_mentions_media = _has_any(
        readme_text,
        [".png", ".jpg", ".jpeg", ".gif", ".mp4", ".webm", "screenshot", "demo", "!["],
    )
    found = bool(media_files) or readme_mentions_media
    if found:
        return CheckResult(
            category="Media",
            status="ok",
            message="Screenshot or demo media hint found.",
            points=10,
            max_points=10,
            details={
                "media_files": media_files[:20],
                "readme_mentions_media": readme_mentions_media,
            },
            explanation=(
                "Media gets 10/10 because media files or README media references were found."
            ),
        )
    return CheckResult(
        category="Media",
        status="warning",
        message="No screenshots or demo media found.",
        points=0,
        max_points=10,
        details={"media_files": [], "readme_mentions_media": False},
        explanation="Media gets 0/10 because no media file or README media reference was found.",
        recommendations=[
            "Add a screenshot or short demo media under docs/assets/ when it helps the project."
        ],
    )


def check_demo(path: Path, config: ShowcaseConfig) -> CheckResult:
    del config
    readme_text = _read_text(path / "README.md").lower()
    hosted_demo = bool(
        re.search(r"https?://[^\s)]+(netlify\.app|vercel\.app|github\.io)", readme_text)
    )
    local_demo = _has_any(
        readme_text,
        [
            "127.0.0.1",
            "localhost",
            "npm run dev",
            "npm start",
            "python -m http.server",
            "streamlit run",
            "uvicorn",
            "flask run",
            "typer",
            "foliolint scan",
            "python -m",
        ],
    )
    if hosted_demo or local_demo:
        message = "Hosted demo link found." if hosted_demo else "Local start instructions found."
        return CheckResult(
            category="Demo",
            status="ok",
            message=message,
            points=10,
            max_points=10,
            details={"hosted_demo": hosted_demo, "local_demo": local_demo},
            explanation="Demo gets 10/10 because hosted or local demo instructions were found.",
        )
    return CheckResult(
        category="Demo",
        status="warning",
        message="No demo link or local start path found.",
        points=0,
        max_points=10,
        details={"hosted_demo": False, "local_demo": False},
        explanation=(
            "Demo gets 0/10 because README.md has no hosted demo link or local start instruction."
        ),
        recommendations=[
            "Document a hosted demo link or a local start command when the project supports it."
        ],
    )


def check_hygiene(path: Path, config: ShowcaseConfig) -> CheckResult:
    generated_dirs: set[str] = set()
    ignored_local_paths: list[str] = []
    env_files: list[str] = []
    log_files: list[str] = []
    large_files: list[str] = []
    threshold_bytes = config.thresholds.large_file_mb * 1024 * 1024
    gitignore_patterns = _read_gitignore_patterns(path)
    tracked_paths = _git_tracked_paths(path)

    for item in _iter_paths(path, config):
        rel = item.relative_to(path).as_posix()
        if tracked_paths is not None:
            is_untracked_hygiene_path = _is_common_hygiene_path(item) and not _is_git_tracked(
                rel, item.is_dir(), tracked_paths
            )
            if is_untracked_hygiene_path:
                ignored_local_paths.append(rel)
                continue
        else:
            if _matches_gitignore(rel, item.is_dir(), gitignore_patterns):
                if _is_common_hygiene_path(item):
                    ignored_local_paths.append(rel)
                continue
        if item.is_dir() and item.name in GENERATED_DIRS:
            generated_dirs.add(rel)
            continue
        if not item.is_file():
            continue
        if item.name == ".env" or item.name.startswith(".env."):
            env_files.append(rel)
        if item.suffix.lower() == ".log":
            log_files.append(rel)
        try:
            if item.stat().st_size > threshold_bytes:
                large_files.append(rel)
        except OSError:
            continue

    penalties = min(6, len(generated_dirs) * 2)
    penalties += min(4, len(large_files) * 3)
    penalties += min(4, len(env_files) * 4)
    penalties += min(3, len(log_files) * 2)
    points = max(0, 15 - penalties)
    has_issues = bool(generated_dirs or env_files or log_files or large_files)
    message = "No common hygiene issues found."
    recommendations = []
    if has_issues:
        parts = []
        if generated_dirs:
            parts.append(f"generated folders: {', '.join(sorted(generated_dirs)[:3])}")
            recommendations.append(
                "Remove generated folders from the repository if they are not needed."
            )
        if large_files:
            parts.append(f"large files: {', '.join(large_files[:3])}")
            recommendations.append(
                "Review large files and move heavy demo assets out of git if needed."
            )
        if env_files:
            parts.append(f"env files: {', '.join(env_files[:3])}")
            recommendations.append(
                "Remove .env files from the repository and keep local settings private."
            )
        if log_files:
            parts.append(f"log files: {', '.join(log_files[:3])}")
            recommendations.append("Remove log files unless they are intentional fixtures.")
        message = "; ".join(parts)
    return CheckResult(
        category="Hygiene",
        status="warning" if has_issues else "ok",
        message=message,
        points=points,
        max_points=15,
        details={
            "generated_dirs": sorted(generated_dirs),
            "large_files": large_files,
            "env_files": env_files,
            "log_files": log_files,
            "ignored_local_paths": ignored_local_paths[:20],
            "uses_git_tracking": tracked_paths is not None,
            "large_file_mb": config.thresholds.large_file_mb,
        },
        explanation=(
            f"Hygiene gets {points}/15 after deductions for generated folders, "
            "large files, env files and logs."
        ),
        recommendations=recommendations,
    )


def check_secrets(path: Path, config: ShowcaseConfig) -> CheckResult:
    matches: list[dict[str, str]] = []
    for file in _iter_files(path, config):
        if _is_in_skipped_secret_dir(file, path):
            continue
        if not _should_scan_text(file):
            continue
        text = _read_text(file)
        if not text:
            continue
        match = _find_secret_hint(text)
        if match is not None:
            matches.append({"path": file.relative_to(path).as_posix(), "pattern": match})

    if matches:
        return CheckResult(
            category="Secrets",
            status="warning",
            message="Obvious secret risk hints found.",
            points=0,
            max_points=10,
            details={"matches": matches[:20]},
            explanation=(
                "Secrets gets 0/10 because obvious risky strings were found. "
                "This is not a full security scan."
            ),
            recommendations=[
                "Review obvious secret risk hints before sharing the repository publicly."
            ],
        )
    return CheckResult(
        category="Secrets",
        status="ok",
        message="No obvious secret patterns found.",
        points=10,
        max_points=10,
        details={"matches": []},
        explanation=(
            "Secrets gets 10/10 because no configured risky strings were found. "
            "This is not a full security scan."
        ),
    )


def check_metadata(path: Path, config: ShowcaseConfig) -> CheckResult:
    del config
    vite_files = list(path.glob("vite.config.*"))
    workflow_details = _github_actions_details(path)
    workflows = bool(workflow_details["files"])
    found = {
        "pyproject.toml": (path / "pyproject.toml").exists(),
        "requirements.txt": (path / "requirements.txt").exists(),
        "package.json": (path / "package.json").exists(),
        "vite.config": bool(vite_files),
        ".github/workflows": workflows,
        "workflow_files": workflow_details["files"],
    }
    points = 0
    if found["pyproject.toml"]:
        points += 2
    for key in ["requirements.txt", "package.json", "vite.config", ".github/workflows"]:
        if found[key]:
            points += 1
    points = min(points, 5)
    status = "ok" if points > 0 else "warning"
    message = "Project metadata found." if points > 0 else "No common project metadata found."
    recommendations = (
        []
        if points > 0
        else ["Add common project metadata such as pyproject.toml or package.json."]
    )
    return CheckResult(
        category="Metadata",
        status=status,
        message=message,
        points=points,
        max_points=5,
        details=found,
        explanation=f"Metadata gets {points}/5 from common project files and workflow metadata.",
        recommendations=recommendations,
    )


def _category_for_id(check_id: str) -> str:
    return {
        README_CHECK_ID: "README",
        LICENSE_CHECK_ID: "License",
        TESTS_CHECK_ID: "Tests",
        MEDIA_CHECK_ID: "Media",
        DEMO_CHECK_ID: "Demo",
        HYGIENE_CHECK_ID: "Hygiene",
        SECRETS_CHECK_ID: "Secrets",
        METADATA_CHECK_ID: "Metadata",
    }[check_id]


def _iter_files(path: Path, config: ShowcaseConfig) -> Iterable[Path]:
    for item in _iter_paths(path, config):
        if item.is_file():
            yield item


def _iter_paths(path: Path, config: ShowcaseConfig) -> Iterable[Path]:
    for item in path.rglob("*"):
        if ".git" in item.parts:
            continue
        if _is_ignored(item, path, config):
            continue
        yield item


def _is_ignored(item: Path, root: Path, config: ShowcaseConfig) -> bool:
    try:
        rel = item.relative_to(root).as_posix()
    except ValueError:
        return False
    ignored = {entry.strip("/\\") for entry in config.ignore.paths}
    return any(rel == entry or rel.startswith(f"{entry}/") for entry in ignored if entry)


def _read_gitignore_patterns(root: Path) -> list[str]:
    gitignore = root / ".gitignore"
    if not gitignore.exists():
        return []
    patterns: list[str] = []
    for line in _read_text(gitignore).splitlines():
        pattern = line.strip()
        if not pattern or pattern.startswith("#") or pattern.startswith("!"):
            continue
        patterns.append(pattern)
    return patterns


def _matches_gitignore(rel_path: str, is_dir: bool, patterns: list[str]) -> bool:
    parts = rel_path.split("/")
    for pattern in patterns:
        normalized = pattern.strip("/")
        if not normalized:
            continue
        dir_only = pattern.endswith("/")
        if dir_only and not is_dir:
            parent_parts = parts[:-1]
            if "/" not in normalized and normalized in parent_parts:
                return True
            if "/".join(parent_parts).startswith(f"{normalized}/"):
                return True
            continue
        if "/" not in normalized and normalized in parts:
            return True
        if rel_path == normalized or rel_path.startswith(f"{normalized}/"):
            return True
    return False


def _is_common_hygiene_path(item: Path) -> bool:
    return (
        item.name in GENERATED_DIRS
        or item.name == ".env"
        or item.name.startswith(".env.")
        or item.suffix.lower() == ".log"
    )


def _git_tracked_paths(root: Path) -> set[str] | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None

    paths = {path for path in result.stdout.split("\0") if path}
    return paths


def _is_git_tracked(rel_path: str, is_dir: bool, tracked_paths: set[str]) -> bool:
    if rel_path in tracked_paths:
        return True
    if is_dir:
        return any(path.startswith(f"{rel_path}/") for path in tracked_paths)
    return False


def _read_text(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _has_any(text: str, needles: list[str]) -> bool:
    return any(needle in text for needle in needles)


def _readme_evidence(text: str) -> dict[str, list[str]]:
    evidence = {key: [] for key in README_HEADINGS}
    headings = _markdown_headings(text)
    code_blocks = _markdown_code_blocks(text)

    for category, aliases in README_HEADINGS.items():
        for heading in headings:
            if any(alias in heading for alias in aliases):
                evidence[category].append(f"heading '{heading}'")
                break

    for category, commands in README_COMMANDS.items():
        for block in code_blocks:
            matched = next((command for command in commands if command in block), None)
            if matched:
                evidence[category].append(f"code command '{matched}'")
                break

    lowered = text.lower()
    if not evidence["screenshot_or_demo"] and (
        "![" in lowered or any(extension in lowered for extension in MEDIA_EXTENSIONS)
    ):
        evidence["screenshot_or_demo"].append("README media reference")

    return evidence


def _markdown_headings(text: str) -> list[str]:
    headings: list[str] = []
    for line in text.splitlines():
        match = re.match(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$", line)
        if match:
            headings.append(match.group(1).strip().lower())
    return headings


def _markdown_code_blocks(text: str) -> list[str]:
    blocks: list[str] = []
    current: list[str] = []
    in_block = False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            if in_block:
                blocks.append("\n".join(current).lower())
                current = []
            in_block = not in_block
            continue
        if in_block:
            current.append(line)
    return blocks


def _readme_explanation(points: int, evidence: dict[str, list[str]]) -> str:
    matched = [
        f"{category}: {', '.join(matches)}" for category, matches in evidence.items() if matches
    ]
    if not matched:
        return f"README gets {points}/25 without key section matches."
    return f"README gets {points}/25. Matches: {'; '.join(matched)}."


def _readme_message(found: dict[str, bool]) -> str:
    labels = {
        "purpose": "purpose",
        "setup": "setup",
        "usage": "usage",
        "tests": "tests",
        "limitations": "status or limitations",
        "screenshot_or_demo": "screenshot or demo",
    }
    present = [label for key, label in labels.items() if found.get(key)]
    if not present:
        return "README.md exists but key showcase sections were not detected."
    return f"README hints found: {', '.join(present)}."


def _package_json_has_test_script(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        package = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    scripts = package.get("scripts", {})
    return isinstance(scripts, dict) and isinstance(scripts.get("test"), str)


def _github_actions_details(path: Path) -> dict[str, object]:
    workflows = path / ".github" / "workflows"
    if not workflows.is_dir():
        return {"files": [], "tools": [], "has_meaningful_checks": False}

    workflow_files = [
        file for file in workflows.iterdir() if file.is_file() and file.suffix in {".yml", ".yaml"}
    ]
    tools: set[str] = set()
    for file in workflow_files:
        text = _read_text(file).lower()
        for tool, hints in WORKFLOW_HINTS.items():
            if any(hint in text for hint in hints):
                tools.add(tool)

    return {
        "files": [file.relative_to(path).as_posix() for file in workflow_files],
        "tools": sorted(tools),
        "has_meaningful_checks": bool(tools),
    }


def _should_scan_text(file: Path) -> bool:
    if file.suffix.lower() not in TEXT_EXTENSIONS and file.name not in {".env"}:
        return False
    try:
        return file.stat().st_size <= 1024 * 1024
    except OSError:
        return False


def _is_in_skipped_secret_dir(file: Path, root: Path) -> bool:
    try:
        relative_parts = file.relative_to(root).parts
    except ValueError:
        return False
    return any(part in SECRET_SCAN_SKIP_DIRS for part in relative_parts[:-1])


def _find_secret_hint(text: str) -> str | None:
    private_key_marker = "BEGIN " + "RSA PRIVATE KEY"
    if private_key_marker in text.upper():
        return private_key_marker
    match = SECRET_ASSIGNMENT_RE.search(text)
    return match.group(1).upper() if match else None
