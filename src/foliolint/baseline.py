from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from foliolint.models import ScanReport

BASELINE_SCHEMA_VERSION = 2


def save_baseline(report: ScanReport, path: Path) -> None:
    data = {
        "schema_version": BASELINE_SCHEMA_VERSION,
        "score": report.score,
        "status": report.status,
        "checks": [
            {
                "category": check.category,
                "status": check.status,
                "points": check.points,
                "max_points": check.max_points,
            }
            for check in report.checks
        ],
    }
    provenance = _provenance_for_report(report)
    if provenance is not None:
        data["provenance"] = provenance
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_baseline(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Could not read baseline file: {path}") from error
    if not isinstance(data, dict) or not isinstance(data.get("checks"), list):
        raise ValueError(f"Invalid FolioLint baseline file: {path}")
    return data


def compare_baseline(report: ScanReport, baseline: dict[str, Any]) -> dict[str, Any]:
    baseline_provenance = _read_provenance(baseline)
    current_provenance = _provenance_for_report(report)
    identity_status = _identity_status(
        baseline_provenance,
        current_provenance,
        is_legacy="schema_version" not in baseline,
    )
    if identity_status == "mismatched":
        raise ValueError(
            "Baseline belongs to a different repository or branch; refusing comparison."
        )

    old_checks = {
        item.get("category"): item
        for item in baseline["checks"]
        if isinstance(item, dict) and isinstance(item.get("category"), str)
    }
    new_checks = {check.category: check for check in report.checks}
    changed: list[dict[str, Any]] = []
    for category, check in new_checks.items():
        previous = old_checks.get(category)
        if previous is None:
            changed.append({"category": category, "change": "added", "status": check.status})
            continue
        if (
            previous.get("status") != check.status
            or previous.get("points") != check.points
            or previous.get("max_points") != check.max_points
        ):
            changed.append(
                {
                    "category": category,
                    "change": "changed",
                    "from": {
                        "status": previous.get("status"),
                        "points": previous.get("points"),
                        "max_points": previous.get("max_points"),
                    },
                    "to": {
                        "status": check.status,
                        "points": check.points,
                        "max_points": check.max_points,
                    },
                }
            )
    for category in old_checks.keys() - new_checks.keys():
        changed.append({"category": category, "change": "removed"})

    old_score = baseline.get("score")
    score_delta = (
        report.score - old_score
        if isinstance(old_score, int) and isinstance(report.score, int)
        else None
    )
    return {
        "baseline_score": old_score,
        "current_score": report.score,
        "score_delta": score_delta,
        "changed_checks": changed,
        "identity_status": identity_status,
    }


def _read_provenance(baseline: dict[str, Any]) -> dict[str, str] | None:
    provenance = baseline.get("provenance")
    if not isinstance(provenance, dict):
        return None
    values = {key: value for key, value in provenance.items() if isinstance(value, str)}
    return values or None


def _provenance_for_report(report: ScanReport) -> dict[str, str] | None:
    if report.remote:
        source_url = report.remote.get("source_url")
        branch = report.remote.get("branch")
        if isinstance(source_url, str) and isinstance(branch, str):
            return {"source_url": normalize_repository_url(source_url), "branch": branch}

    origin = _local_origin(Path(report.path))
    if origin is not None:
        return {"origin": normalize_repository_url(origin)}
    return None


def normalize_repository_url(url: str) -> str:
    """Return equivalent HTTP and SSH repository URLs in one stable form."""
    value = url.strip().rstrip("/")
    parsed = urlparse(value)
    if parsed.scheme and parsed.hostname:
        return _normalized_parts(parsed.hostname, parsed.path)
    scp_style = re.fullmatch(r"(?:[^@]+@)?([^:/]+):/?(.+)", value)
    if scp_style:
        host, path = scp_style.groups()
        return _normalized_parts(host, path)
    return value.removesuffix(".git")


def _normalized_parts(host: str, path: str) -> str:
    normalized_path = path.strip("/").removesuffix(".git")
    if host.lower() == "github.com":
        normalized_path = normalized_path.lower()
    return f"https://{host.lower()}/{normalized_path}"


def _local_origin(path: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(path), "config", "--get", "remote.origin.url"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    origin = result.stdout.strip()
    return origin if result.returncode == 0 and origin else None


def _identity_status(
    baseline_provenance: dict[str, str] | None,
    current_provenance: dict[str, str] | None,
    *,
    is_legacy: bool,
) -> str:
    if baseline_provenance is None:
        return "legacy_unverified" if is_legacy else "unverified"
    if current_provenance is None:
        return "unverified"
    return "matched" if baseline_provenance == current_provenance else "mismatched"
