from __future__ import annotations

import re
from pathlib import Path

from foliolint.check_metadata import README
from foliolint.checks.common import _has_any_term, _read_text
from foliolint.config import ShowcaseConfig
from foliolint.models import CheckResult


def check_readme(path: Path, config: ShowcaseConfig) -> CheckResult:
    del config
    readme = path / "README.md"
    if not readme.exists():
        return CheckResult(
            category=README.category,
            status="warning",
            message="No README.md file found.",
            points=0,
            max_points=README.max_points,
            details={"exists": False},
            explanation="README gets 0/25 because README.md is missing.",
            recommendations=["Add a README.md with purpose, setup, usage and current limits."],
        )

    text = _read_text(readme)
    lowered = text.lower()
    evidence = _readme_evidence(text)
    for section, matches in evidence.items():
        if matches:
            continue
        terms = README_HEADINGS[section] + README_EXTRA_TERMS.get(section, [])
        if section == "screenshot_or_demo":
            # A heading like "Preview" counts, but the word alone in prose does not.
            terms = ["screenshot", "demo"]
        if _has_any_term(lowered, terms) or (
            section == "purpose" and _looks_like_project_description(text)
        ):
            matches.append("keyword or content heuristic")

    found = {"exists": True, **{section: bool(matches) for section, matches in evidence.items()}}
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
        category=README.category,
        status=status,
        message=message,
        points=points,
        max_points=README.max_points,
        details={**found, "matches": evidence},
        explanation=_readme_explanation(points, evidence),
        recommendations=recommendations,
    )


def _looks_like_project_description(text: str) -> bool:
    paragraphs = [
        paragraph.strip()
        for paragraph in re.split(r"\n\s*\n", text)
        if paragraph.strip() and not paragraph.lstrip().startswith("#")
    ]
    if not paragraphs:
        return False
    first = re.sub(r"[`*_\[\]()]", "", paragraphs[0])
    return len(first.split()) >= 8 and bool(
        re.search(r"\b(is|helps|provides|builds|shows|creates)\b", first, re.I)
    )


def _readme_media_reference(text: str) -> bool:
    return bool(
        re.search(
            r"!\[[^\]]*\]\([^)]+\.(?:png|jpe?g|gif|mp4|webm)(?:\?[^)]*)?\)",
            text,
            re.IGNORECASE,
        )
    )


def _readme_evidence(text: str) -> dict[str, list[str]]:
    evidence = {key: [] for key in README_HEADINGS}
    headings = _markdown_headings(text)
    code_blocks = _markdown_code_blocks(text)

    for category, aliases in README_HEADINGS.items():
        for heading in headings:
            if _has_any_term(heading, aliases):
                evidence[category].append(f"heading '{heading}'")
                break

    for category, commands in README_COMMANDS.items():
        for block in code_blocks:
            matched = next((command for command in commands if command in block), None)
            if matched:
                evidence[category].append(f"code command '{matched}'")
                break

    if not evidence["screenshot_or_demo"] and _readme_media_reference(text):
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
        "limitations": "status or limitations",
        "screenshot_or_demo": "screenshot or demo",
    }
    present = [labels.get(section, section) for section in README_HEADINGS if found[section]]
    if not present:
        return "README.md exists but key showcase sections were not detected."
    return f"README hints found: {', '.join(present)}."


README_HEADINGS = {
    "purpose": ["about", "overview", "description", "purpose", "what is", "ziel", "zweck"],
    "setup": ["installation", "install", "setup", "requirements"],
    "usage": ["usage", "quick start", "getting started", "how to run", "nutzung"],
    "tests": ["tests", "testing", "test suite"],
    "limitations": ["status", "limitations", "limits", "roadmap", "grenzen"],
    "screenshot_or_demo": ["demo", "screenshot", "screenshots", "preview"],
}

README_EXTRA_TERMS = {
    "purpose": ["this project", "a tool", "a library", "a cli", "an app"],
    "setup": ["pip install", "npm install", "venv"],
    "usage": ["benutzung"],
    "tests": ["pytest", "unittest", "npm test", "coverage"],
    "limitations": ["prototype", "wip"],
}


README_COMMANDS = {
    "setup": ["pip install", "npm install", "python -m venv"],
    "usage": ["python -m", "npm run dev", "npm start", "foliolint scan"],
    "tests": ["pytest", "python -m pytest", "npm test", "npm run test"],
}
