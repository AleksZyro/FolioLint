from __future__ import annotations

from html import escape

from rich.console import Console
from rich.table import Table

from foliolint.models import ScanReport


def render_text_report(
    report: ScanReport,
    *,
    include_score: bool = True,
    explain: bool = False,
    details: bool = False,
    console: Console | None = None,
) -> None:
    output = console or Console()
    output.print("[bold]FolioLint[/bold]")
    output.print()
    output.print(f"Path: {report.path}")
    if report.remote:
        output.print(f"Remote: {report.remote['source_url']}")
        output.print(f"Branch: {report.remote['branch']}")
        output.print("Temporary copy: removed after scan")
    if include_score:
        output.print(f"Score: {report.score}/100")
        output.print(f"Status: {report.status}")
    output.print()

    table = Table(show_header=True, header_style="bold")
    table.add_column("Category")
    table.add_column("Status")
    table.add_column("Notes")
    if explain:
        table.add_column("Points")
    for check in report.checks:
        status = check.status.capitalize()
        points = f"{check.points}/{check.max_points}" if check.max_points else "-"
        row = [check.category, status, check.message]
        if explain:
            row.append(points)
        table.add_row(*row)
    output.print(table)

    if explain:
        output.print()
        output.print("[bold]Explanation[/bold]")
        for check in report.checks:
            output.print(f"- {check.category}: {check.explanation}")

    if details:
        output.print()
        output.print("[bold]Details[/bold]")
        for check in report.checks:
            detail_lines = _detail_lines(check.details)
            if not detail_lines:
                continue
            output.print(f"- {check.category}:")
            for line in detail_lines:
                output.print(f"  - {line}")

    if report.recommendations:
        output.print()
        output.print("[bold]Recommended next steps:[/bold]")
        for index, recommendation in enumerate(report.recommendations, start=1):
            output.print(f"{index}. {recommendation}")


def render_markdown_report(
    report: ScanReport,
    *,
    include_score: bool = True,
    details: bool = False,
) -> str:
    lines = ["# FolioLint Report", ""]
    lines.append(f"Path: `{report.path}`")
    if report.remote:
        lines.append(f"Remote: `{report.remote['source_url']}`")
        lines.append(f"Branch: `{report.remote['branch']}`")
        lines.append("Temporary copy: removed after scan")
    if include_score:
        lines.append(f"Score: **{report.score}/100**")
        lines.append(f"Status: **{report.status}**")
    lines.extend(
        [
            "",
            "| Category | Status | Points | Notes |",
            "| --- | --- | ---: | --- |",
        ]
    )
    for check in report.checks:
        points = f"{check.points}/{check.max_points}" if check.max_points else "-"
        lines.append(
            "| "
            f"{_escape_markdown_table(check.category)} | "
            f"{check.status} | "
            f"{points} | "
            f"{_escape_markdown_table(check.message)} |"
        )

    if details:
        lines.extend(["", "## Details", ""])
        for check in report.checks:
            detail_lines = _detail_lines(check.details)
            if not detail_lines:
                continue
            lines.append(f"### {check.category}")
            for line in detail_lines:
                lines.append(f"- {line}")
            lines.append("")

    if report.recommendations:
        lines.extend(["", "## Recommended Next Steps", ""])
        for index, recommendation in enumerate(report.recommendations, start=1):
            lines.append(f"{index}. {recommendation}")

    return "\n".join(lines) + "\n"


def render_html_report(
    report: ScanReport,
    *,
    include_score: bool = True,
    details: bool = False,
    baseline: dict | None = None,
) -> str:
    score_block = ""
    if include_score:
        score_block = (
            f'<div class="score"><strong>{escape(str(report.score))}/100</strong>'
            f"<span>{escape(report.status or '')}</span></div>"
        )
    rows = []
    for check in report.checks:
        points = f"{check.points}/{check.max_points}" if check.max_points else "-"
        detail = ""
        if details:
            detail_lines = _detail_lines(check.details)
            if detail_lines:
                detail = f'<div class="details">{escape("; ".join(detail_lines))}</div>'
        rows.append(
            "<tr>"
            f"<td>{escape(check.category)}</td>"
            f'<td class="status-{escape(check.status)}">{escape(check.status)}</td>'
            f"<td>{escape(points)}</td>"
            f"<td>{escape(check.message)}{detail}</td>"
            "</tr>"
        )
    recommendations = "".join(f"<li>{escape(item)}</li>" for item in report.recommendations)
    remote_block = ""
    if report.remote:
        remote_block = (
            f"<p>Remote: <code>{escape(str(report.remote.get('source_url', '')))}</code>"
            f" on branch <code>{escape(str(report.remote.get('branch', '')))}</code></p>"
            "<p>Temporary copy: removed after scan</p>"
        )
    baseline_block = ""
    if baseline is not None:
        baseline_block = (
            "<h2>Baseline comparison</h2><pre>" + escape(_format_baseline(baseline)) + "</pre>"
        )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FolioLint report</title>
<style>
body {{ background:#10141b; color:#e8edf3; font:16px/1.5 system-ui,sans-serif; margin:0; }}
main {{ max-width:1000px; margin:40px auto; padding:0 24px; }}
.score {{ display:flex; gap:20px; align-items:baseline; margin:20px 0; }}
.score strong {{ color:#72b7ff; font-size:2rem; }}
.score span {{ color:#9fe3ad; }}
table {{ border-collapse:collapse; width:100%; background:#171d26; }}
th,td {{ border-bottom:1px solid #303947; padding:12px; text-align:left; vertical-align:top; }}
th {{ color:#aebbd0; }}
.status-ok {{ color:#82d994; }} .status-warning {{ color:#ffd27d; }}
.status-ignored {{ color:#aebbd0; }} .details {{ color:#aebbd0; font-size:.9rem; margin-top:6px; }}
li {{ margin:8px 0; }} pre {{ white-space:pre-wrap; background:#171d26; padding:16px; }}
</style>
</head>
<body><main><h1>FolioLint Report</h1>
<p>Path: <code>{escape(report.path)}</code></p>{remote_block}{score_block}
<table><thead><tr><th>Category</th><th>Status</th><th>Points</th><th>Notes</th></tr></thead>
<tbody>{"".join(rows)}</tbody></table>
{("<h2>Recommended next steps</h2><ol>" + recommendations + "</ol>") if recommendations else ""}
{baseline_block}
</main></body></html>
"""


def _format_baseline(baseline: dict) -> str:
    delta = baseline.get("score_delta")
    delta_text = "n/a" if delta is None else f"{delta:+}"
    lines = [
        f"Score: {baseline.get('baseline_score')} -> {baseline.get('current_score')} ({delta_text})"
    ]
    status = baseline.get("identity_status")
    if status == "legacy_unverified":
        lines.append("Repository identity: not verified (legacy baseline)")
    elif status == "unverified":
        lines.append("Repository identity: not verified")
    elif status == "matched":
        lines.append("Repository identity: matched")
    for change in baseline.get("changed_checks", []):
        lines.append(f"- {change.get('category')}: {change.get('change')}")
    if len(lines) == 1:
        lines.append("- No category changes")
    return "\n".join(lines)


def _escape_markdown_table(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _detail_lines(details: dict) -> list[str]:
    lines: list[str] = []
    matches = details.get("matches")
    if isinstance(matches, dict):
        for name, values in matches.items():
            if isinstance(values, list) and values:
                lines.append(f"{name}: {', '.join(str(value) for value in values[:4])}")
    elif isinstance(matches, list) and matches:
        for match in matches[:8]:
            if isinstance(match, dict):
                path = match.get("path", "unknown path")
                pattern = match.get("pattern", "unknown pattern")
                line = match.get("line")
                location = f"{path}:{line}" if line else str(path)
                lines.append(f"{location}: {pattern}")

    for key in [
        "test_files",
        "github_actions_files",
        "github_actions_tools",
        "media_files",
        "generated_dirs",
        "large_files",
        "env_files",
        "log_files",
        "ignored_local_paths",
        "workflow_files",
        "project_type_evidence",
    ]:
        value = details.get(key)
        if isinstance(value, list) and value:
            lines.append(f"{key}: {', '.join(str(item) for item in value[:8])}")

    for key in [
        "tests_dir",
        "package_json_test_script",
        "github_actions",
        "hosted_demo",
        "local_demo",
        "readme_mentions_media",
        "uses_git_tracking",
        "large_file_mb",
    ]:
        if key in details:
            lines.append(f"{key}: {details[key]}")

    return lines[:12]
