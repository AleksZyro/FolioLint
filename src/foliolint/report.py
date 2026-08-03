from __future__ import annotations

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
