"""GitHub workflow commands rendered offline from existing check evidence."""

from collections.abc import Iterable

from foliolint.check_metadata import DEMO, HYGIENE, README, SECRETS
from foliolint.models import CheckResult, ScanReport


def _escape(value: str, *, property_value: bool = False) -> str:
    value = value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    if property_value:
        value = value.replace(":", "%3A").replace(",", "%2C")
    return value


def _locations(check: CheckResult, *, readme_exists: bool) -> Iterable[tuple[str, str | None]]:
    if check.category in {README.category, DEMO.category} and readme_exists:
        yield "README.md", None
    elif check.category == HYGIENE.category:
        for key in ("large_files", "env_files", "log_files"):
            for path in check.details.get(key, []):
                yield path, None
    elif check.category == SECRETS.category:
        for match in check.details.get("matches", []):
            yield match["path"], match.get("line")


def render_github_report(report: ScanReport, *, include_score: bool = True) -> str:
    """Annotate only evidenced files; general and remote warnings remain log text.

    A scan-url target is not necessarily the repository checked out by the runner.
    No file annotations are emitted for remote scans to avoid misleading associations.
    """
    lines = []
    if include_score:
        lines.append(f"FolioLint score: {report.score}/100 ({_escape(report.status or '')})")
    readme_exists = any(
        check.category == README.category and check.details.get("exists") for check in report.checks
    )
    for check in report.checks:
        if check.status != "warning":
            continue
        message = _escape(f"{check.category}: {check.message}")
        locations = [] if report.remote else list(_locations(check, readme_exists=readme_exists))
        if not locations:
            lines.append(f"FolioLint warning: {message}")
            continue
        for path, line in dict.fromkeys(locations):
            properties = "file=" + _escape(path, property_value=True)
            if line is not None and str(line).isdigit() and int(line) > 0:
                properties += f",line={int(line)}"
            lines.append(f"::warning {properties}::{message}")
    return "\n".join(lines) + ("\n" if lines else "")
