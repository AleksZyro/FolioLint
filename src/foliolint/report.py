from __future__ import annotations

from rich.console import Console
from rich.table import Table

from foliolint.models import ScanReport


def render_text_report(
    report: ScanReport,
    *,
    include_score: bool = True,
    explain: bool = False,
    console: Console | None = None,
) -> None:
    output = console or Console()
    output.print("[bold]FolioLint[/bold]")
    output.print()
    output.print(f"Path: {report.path}")
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

    if report.recommendations:
        output.print()
        output.print("[bold]Recommended next steps:[/bold]")
        for index, recommendation in enumerate(report.recommendations, start=1):
            output.print(f"{index}. {recommendation}")

