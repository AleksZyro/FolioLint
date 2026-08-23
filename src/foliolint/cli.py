from __future__ import annotations

import json
from dataclasses import replace
from enum import StrEnum
from io import StringIO
from pathlib import Path
from typing import Annotated

import typer

from foliolint.baseline import compare_baseline, load_baseline, save_baseline
from foliolint.config import CONFIG_FILE, DEFAULT_CONFIG
from foliolint.remote import DEFAULT_MAX_DOWNLOAD_MB, RemoteScanError, prepare_remote_repository
from foliolint.report import render_html_report, render_markdown_report, render_text_report
from foliolint.scanner import scan_project


class OutputFormat(StrEnum):
    text = "text"
    json = "json"
    markdown = "markdown"
    html = "html"


PathArgument = Annotated[
    Path,
    typer.Argument(exists=True, file_okay=False, dir_okay=True, readable=True),
]
NoScoreOption = Annotated[
    bool,
    typer.Option("--no-score", help="Show checks without overall score."),
]
ExplainOption = Annotated[
    bool,
    typer.Option("--explain", help="Explain category points."),
]
DetailsOption = Annotated[
    bool,
    typer.Option("--details", help="Show file and pattern details for checks."),
]
FormatOption = Annotated[
    OutputFormat,
    typer.Option("--format", case_sensitive=False, help="Output format."),
]
StrictOption = Annotated[
    bool,
    typer.Option("--strict", help="Use stricter readiness scoring for public presentation."),
]
FailUnderOption = Annotated[
    int | None,
    typer.Option(
        "--fail-under",
        min=0,
        max=100,
        help="Exit with code 1 when the score is below this value.",
    ),
]
RepoUrlArgument = Annotated[
    str,
    typer.Argument(help="Public GitHub repository URL, for example https://github.com/OWNER/REPO."),
]
BranchOption = Annotated[
    str | None,
    typer.Option("--branch", help="Branch to download. Defaults to main, then master."),
]
MaxDownloadOption = Annotated[
    int,
    typer.Option(
        "--max-download-mb",
        min=1,
        help="Maximum ZIP download size for scan-url.",
    ),
]
OutputPathOption = Annotated[
    Path | None,
    typer.Option("--output", help="Write the report to a file instead of the terminal."),
]
SaveBaselineOption = Annotated[
    Path | None,
    typer.Option(
        "--save-baseline", help="Save the current score and check results to a JSON file."
    ),
]
CompareBaselineOption = Annotated[
    Path | None,
    typer.Option("--compare-baseline", help="Compare this scan with a saved baseline JSON file."),
]
InitPathArgument = Annotated[
    Path,
    typer.Argument(help="Folder where the config should be created."),
]


app = typer.Typer(no_args_is_help=True, help="Check local repository showcase readiness.")


@app.callback()
def main() -> None:
    """FolioLint command group."""


@app.command()
def scan(
    path: PathArgument,
    no_score: NoScoreOption = False,
    explain: ExplainOption = False,
    details: DetailsOption = False,
    output_format: FormatOption = OutputFormat.text,
    strict: StrictOption = False,
    fail_under: FailUnderOption = None,
    output: OutputPathOption = None,
    save_baseline_path: SaveBaselineOption = None,
    compare_baseline_path: CompareBaselineOption = None,
) -> None:
    """Scan a repository path."""
    if no_score and fail_under is not None:
        typer.echo("Error: --fail-under cannot be used together with --no-score.", err=True)
        raise typer.Exit(2)

    report = scan_project(path, include_score=not no_score, strict=strict)
    baseline = _handle_baseline(report, save_baseline_path, compare_baseline_path)
    if output_format == OutputFormat.json:
        content = json.dumps(
            _report_data(report, not no_score, explain, details, baseline), indent=2, sort_keys=True
        )
        _emit(content, output)
        _exit_if_under_threshold(report.score, fail_under)
        return
    if output_format == OutputFormat.markdown:
        _emit(
            render_markdown_report(report, include_score=not no_score, details=details)
            + _baseline_markdown(baseline),
            output,
        )
        _exit_if_under_threshold(report.score, fail_under)
        return
    if output_format == OutputFormat.html:
        _emit(
            render_html_report(
                report, include_score=not no_score, details=details, baseline=baseline
            ),
            output,
        )
        _exit_if_under_threshold(report.score, fail_under)
        return
    _emit_text_report(
        report,
        include_score=not no_score,
        explain=explain,
        details=details,
        output=output,
        baseline=baseline,
    )
    _exit_if_under_threshold(report.score, fail_under)


@app.command("scan-url")
def scan_url(
    url: RepoUrlArgument,
    branch: BranchOption = None,
    no_score: NoScoreOption = False,
    explain: ExplainOption = False,
    details: DetailsOption = False,
    output_format: FormatOption = OutputFormat.text,
    strict: StrictOption = False,
    fail_under: FailUnderOption = None,
    max_download_mb: MaxDownloadOption = DEFAULT_MAX_DOWNLOAD_MB,
    output: OutputPathOption = None,
    save_baseline_path: SaveBaselineOption = None,
    compare_baseline_path: CompareBaselineOption = None,
) -> None:
    """Download a public GitHub repository ZIP temporarily and scan it."""
    if no_score and fail_under is not None:
        typer.echo("Error: --fail-under cannot be used together with --no-score.", err=True)
        raise typer.Exit(2)

    try:
        with prepare_remote_repository(
            url,
            branch=branch,
            max_download_mb=max_download_mb,
        ) as remote:
            report = scan_project(remote.path, include_score=not no_score, strict=strict)
            report = replace(
                report,
                remote={
                    "source_url": url,
                    "branch": remote.branch,
                    "temporary_copy": "removed after scan",
                },
            )
            baseline = _handle_baseline(report, save_baseline_path, compare_baseline_path)
    except RemoteScanError as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(2) from error

    _render_report(
        report,
        include_score=not no_score,
        explain=explain,
        details=details,
        output_format=output_format,
        output=output,
        baseline=baseline,
    )
    _exit_if_under_threshold(report.score, fail_under)


def _render_report(
    report,
    *,
    include_score: bool,
    explain: bool,
    details: bool,
    output_format: OutputFormat,
    output: Path | None,
    baseline: dict | None,
) -> None:
    if output_format == OutputFormat.json:
        content = json.dumps(
            _report_data(report, include_score, explain, details, baseline),
            indent=2,
            sort_keys=True,
        )
        _emit(content, output)
        return
    if output_format == OutputFormat.markdown:
        _emit(
            render_markdown_report(report, include_score=include_score, details=details)
            + _baseline_markdown(baseline),
            output,
        )
        return
    if output_format == OutputFormat.html:
        _emit(
            render_html_report(
                report, include_score=include_score, details=details, baseline=baseline
            ),
            output,
        )
        return
    _emit_text_report(
        report,
        include_score=include_score,
        explain=explain,
        details=details,
        output=output,
        baseline=baseline,
    )


@app.command()
def init(path: InitPathArgument = Path(".")) -> None:
    """Create a commented example configuration without overwriting files."""
    target = path.resolve()
    if not target.is_dir():
        typer.echo(f"Error: Folder does not exist: {path}", err=True)
        raise typer.Exit(2)
    config_path = target / CONFIG_FILE
    if config_path.exists():
        typer.echo(f"Error: {CONFIG_FILE} already exists; it was not changed.", err=True)
        raise typer.Exit(2)
    try:
        config_path.write_text(DEFAULT_CONFIG, encoding="utf-8")
    except OSError as error:
        typer.echo(f"Error: Could not create {config_path}: {error}", err=True)
        raise typer.Exit(2) from error
    typer.echo(f"Created {config_path}")


def _emit(content: str, output: Path | None) -> None:
    if output is None:
        typer.echo(content, nl=not content.endswith("\n"))
        return
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(content if content.endswith("\n") else content + "\n", encoding="utf-8")
    except OSError as error:
        typer.echo(f"Error: Could not write report to {output}: {error}", err=True)
        raise typer.Exit(2) from error
    typer.echo(f"Report written to {output}")


def _emit_text_report(
    report,
    *,
    include_score: bool,
    explain: bool,
    details: bool,
    output: Path | None,
    baseline: dict | None,
) -> None:
    if output is None:
        render_text_report(report, include_score=include_score, explain=explain, details=details)
        if baseline is not None:
            typer.echo()
            typer.echo("Baseline comparison")
            typer.echo(_baseline_text(baseline))
        return
    from rich.console import Console

    buffer = StringIO()
    console = Console(file=buffer, width=120, color_system=None, force_terminal=False)
    render_text_report(
        report,
        include_score=include_score,
        explain=explain,
        details=details,
        console=console,
    )
    if baseline is not None:
        console.print()
        console.print("Baseline comparison")
        console.print(_baseline_text(baseline))
    _emit(buffer.getvalue(), output)


def _handle_baseline(report, save_path: Path | None, compare_path: Path | None) -> dict | None:
    comparison = None
    if compare_path is not None:
        try:
            comparison = compare_baseline(report, load_baseline(compare_path))
        except ValueError as error:
            typer.echo(f"Error: {error}", err=True)
            raise typer.Exit(2) from error
    if save_path is not None:
        try:
            save_baseline(report, save_path)
        except OSError as error:
            typer.echo(f"Error: Could not save baseline to {save_path}: {error}", err=True)
            raise typer.Exit(2) from error
        typer.echo(f"Baseline written to {save_path}", err=True)
    return comparison


def _report_data(
    report, include_score: bool, explain: bool, details: bool, baseline: dict | None
) -> dict:
    data = report.to_dict(
        include_score=include_score,
        include_explanation=explain,
        include_details=details,
    )
    if baseline is not None:
        data["baseline"] = baseline
    return data


def _baseline_text(baseline: dict) -> str:
    delta = baseline.get("score_delta")
    delta_text = "n/a" if delta is None else f"{delta:+}"
    changes = baseline.get("changed_checks", [])
    lines = [
        f"Score: {baseline.get('baseline_score')} -> {baseline.get('current_score')} ({delta_text})"
    ]
    lines.extend(f"- {item['category']}: {item['change']}" for item in changes)
    return "\n".join(lines) if changes else lines[0] + "\n- No category changes"


def _baseline_markdown(baseline: dict | None) -> str:
    if baseline is None:
        return ""
    return "\n## Baseline Comparison\n\n```text\n" + _baseline_text(baseline) + "\n```\n"


def _exit_if_under_threshold(score: int | None, fail_under: int | None) -> None:
    if fail_under is not None and score is not None and score < fail_under:
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
