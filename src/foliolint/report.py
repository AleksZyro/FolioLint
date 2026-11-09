from __future__ import annotations

from collections import Counter
from html import escape

from rich.console import Console
from rich.table import Table
from rich.text import Text

from foliolint.models import ScanReport

STATUS_LABELS = {"ok": "OK", "warning": "Warning", "ignored": "Ignored"}
STATUS_STYLES = {"ok": "green", "warning": "bold yellow", "ignored": "dim"}


def _check_summary(report: ScanReport) -> str:
    counts = Counter(check.status for check in report.checks)
    return f"{counts['ok']} passed  /  {counts['warning']} warnings  /  {counts['ignored']} ignored"


def render_text_report(
    report: ScanReport,
    *,
    include_score: bool = True,
    explain: bool = False,
    details: bool = False,
    baseline: dict | None = None,
    console: Console | None = None,
) -> None:
    output = console or Console()
    output.print("[bold]FolioLint[/bold]  [dim]Repository readiness[/dim]")
    if include_score:
        output.print(
            Text.assemble(
                ("Score: ", "bold"),
                (f"{report.score}/100", "bold cyan"),
                f"  |  Status: {report.status}",
            )
        )
    output.print(Text(_check_summary(report), style="dim"))
    output.print()
    output.print(Text(f"Path: {report.path}"))
    if report.remote:
        output.print(Text(f"Remote: {report.remote['source_url']}"))
        output.print(Text(f"Branch: {report.remote['branch']}"))
        output.print("Temporary copy: removed after scan")
    output.print()

    if output.width < 64:
        for check in report.checks:
            heading = Text.assemble((check.category, "bold"), "  ", _status_text(check.status))
            if explain:
                heading.append(f"  |  {_points(check.points, check.max_points)} points")
            output.print(heading)
            output.print(Text(f"  {check.message}"))
    else:
        table = Table(box=None, header_style="bold", pad_edge=False, expand=True)
        table.add_column("Category", style="bold", no_wrap=True)
        table.add_column("Status", no_wrap=True)
        if explain:
            table.add_column("Points", justify="right", no_wrap=True)
        table.add_column("Notes", ratio=1)
        for check in report.checks:
            cells = [Text(check.category), _status_text(check.status)]
            if explain:
                cells.append(Text(_points(check.points, check.max_points)))
            table.add_row(*cells, Text(check.message))
        output.print(table)

    if explain:
        output.print()
        output.print("[bold]Explanation[/bold]")
        for check in report.checks:
            output.print(Text(f"- {check.category}: {check.explanation}"))

    if details:
        evidence = [(check.category, _detail_lines(check.details)) for check in report.checks]
        if any(lines for _, lines in evidence):
            output.print("\n[bold]Details[/bold]")
            for category, lines in evidence:
                if lines:
                    output.print(Text(category, style="bold"))
                    for line in lines:
                        output.print(Text(f"  - {line}"))

    if report.recommendations:
        output.print()
        output.print("[bold]Recommended next steps:[/bold]")
        for index, recommendation in enumerate(report.recommendations, start=1):
            output.print(Text(f"{index}. {recommendation}"))

    if baseline is not None:
        output.print("\n[bold]Baseline comparison[/bold]")
        output.print(Text(format_baseline(baseline)))


def _status_text(status: str) -> Text:
    return Text(STATUS_LABELS[status], style=STATUS_STYLES[status])


def _points(points: int, maximum: int) -> str:
    return f"{points}/{maximum}" if maximum else "-"


def render_markdown_report(
    report: ScanReport,
    *,
    include_score: bool = True,
    details: bool = False,
    baseline: dict | None = None,
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
        points = _points(check.points, check.max_points)
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

    if baseline is not None:
        lines.extend(
            ["", "## Baseline Comparison", "", "```text", format_baseline(baseline), "```"]
        )
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
            '<div class="score"><span class="eyebrow">Readiness score</span>'
            f"<strong>{escape(str(report.score))}<small>/100</small></strong>"
            f"<span>{escape(report.status or '')}</span></div>"
        )
    cards = []
    for check in report.checks:
        evidence = _detail_lines(check.details) if details else []
        evidence_block = (
            '<div class="evidence"><strong>Evidence</strong><ul>'
            + "".join(f"<li>{escape(line)}</li>" for line in evidence)
            + "</ul></div>"
            if evidence
            else ""
        )
        points = _points(check.points, check.max_points)
        cards.append(
            '<article class="check"><header>'
            f"<h3>{escape(check.category)}</h3>"
            f'<span class="badge status-{check.status}">{STATUS_LABELS[check.status]}</span>'
            f'<span class="points">{"Points: " + points if check.max_points else "Unscored"}</span>'
            "</header>"
            f"<p>{escape(check.message)}</p>{evidence_block}</article>"
        )
    recommendations = "".join(f"<li>{escape(item)}</li>" for item in report.recommendations)
    next_steps = (
        '<section class="surface"><h2>Recommended next steps</h2>'
        f"<ol>{recommendations}</ol></section>"
        if recommendations
        else ""
    )
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
            '<section class="surface"><h2>Baseline comparison</h2>'
            f"<pre>{escape(format_baseline(baseline))}</pre></section>"
        )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FolioLint report</title>
<style>{_HTML_STYLES}</style>
</head>
<body><main>
<header class="surface overview">
  <div><p class="eyebrow">Repository readiness</p><h1>FolioLint Report</h1>
  <p class="summary">{_check_summary(report)}</p>
  <div class="context"><p>Path: <code>{escape(report.path)}</code></p>{remote_block}</div></div>
  {score_block}
</header>
{next_steps}
<section><h2>Check results</h2><div class="checks">{"".join(cards)}</div></section>
{baseline_block}
</main></body></html>
"""


def format_baseline(baseline: dict) -> str:
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
    changes = baseline.get("changed_checks", [])
    for change in changes:
        lines.append(f"- {change.get('category')}: {change.get('change')}")
    if not changes:
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


_HTML_STYLES = """
* { box-sizing: border-box; }
body {
  color-scheme: light;
  background: #f3f6f8; color: #142637; margin: 0;
  font: 1rem/1.55 system-ui, sans-serif;
}
main {
  display: grid; gap: 1.5rem; max-width: 65rem; margin: auto;
  padding: clamp(1rem, 4vw, 3rem); overflow-wrap: anywhere;
}
h1, h2, h3, p { margin: 0; }
h1 { font-size: clamp(1.9rem, 5vw, 3rem); line-height: 1.1; letter-spacing: -.04em; }
h2 { font-size: 1.3rem; margin-bottom: .75rem; }
h3 { font-size: 1.05rem; }
.surface, .check {
  background: #fff; border: 1px solid #d6e0e8; border-radius: .75rem; padding: 1rem;
}
.surface { padding: clamp(1rem, 3vw, 1.75rem); }
.overview {
  display: grid; grid-template-columns: minmax(0, 1fr) minmax(11rem, 15rem);
  gap: 1.25rem; align-items: start; border-top: .25rem solid #146575;
}
.eyebrow {
  display: block; color: #155968; font-size: .75rem;
  font-weight: 750; text-transform: uppercase; letter-spacing: .09em;
}
.overview h1 { margin-top: .3rem; }
.summary { margin-top: .65rem; font-weight: 650; }
.context { margin-top: .85rem; font-size: .875rem; color: #465768; }
.context p + p { margin-top: .25rem; }
.score {
  display: grid; gap: .2rem; background: #e9f4f5; border: 1px solid #cadfe2;
  border-radius: .55rem; padding: .9rem 1rem; color: #164a55;
}
.score strong { font-size: 2.5rem; line-height: 1.15; font-variant-numeric: tabular-nums; }
.score small { font-size: 1rem; margin-left: .25rem; }
.checks { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .75rem; }
.check header { display: flex; flex-wrap: wrap; gap: .35rem .65rem; align-items: baseline; }
.check p { margin-top: .4rem; }
.badge, .points { font-size: .8125rem; font-weight: 650; }
.badge { border-radius: .35rem; padding: .05rem .45rem; }
.status-ok { background: #e7f4ee; color: #185a3d; }
.status-warning { background: #fff2dc; color: #783c00; }
.status-ignored { background: #edf0f4; color: #43536a; }
.points { margin-left: auto; color: #465768; font-variant-numeric: tabular-nums; }
.evidence {
  border-top: 1px solid #d6e0e8; margin-top: .65rem; padding-top: .5rem;
  color: #465768; font-size: .875rem;
}
ol, ul { margin: .35rem 0 0; padding-left: 1.3rem; }
li + li { margin-top: .25rem; }
pre { white-space: pre-wrap; margin: 0; }
@media (max-width: 42rem) {
  .overview, .checks { grid-template-columns: minmax(0, 1fr); }
}
@media print {
  @page { margin: 14mm; }
  body { background: #fff; color: #000; font-size: 10pt; }
  main, .checks { display: block; padding: 0; max-width: none; }
  section, .overview { margin-bottom: 1rem; }
  .check { margin-bottom: .45rem; }
  .check, .overview { break-inside: avoid; }
  .surface, .check, .score { border-radius: 0; }
  .score, .badge { color: #000; background: transparent; }
  .badge { border: 1px solid #777; }
  h2, h3 { break-after: avoid; }
}
"""
