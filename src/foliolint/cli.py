from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer

from foliolint.remote import RemoteScanError, prepare_remote_repository
from foliolint.report import render_markdown_report, render_text_report
from foliolint.scanner import scan_project


class OutputFormat(StrEnum):
    text = "text"
    json = "json"
    markdown = "markdown"


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


app = typer.Typer(no_args_is_help=True, help="Check local repository showcase readiness.")


@app.callback()
def main() -> None:
    """FolioLint command group."""


@app.command()
def scan(
    path: PathArgument,
    no_score: NoScoreOption = False,
    explain: ExplainOption = False,
    output_format: FormatOption = OutputFormat.text,
    strict: StrictOption = False,
    fail_under: FailUnderOption = None,
) -> None:
    """Scan a repository path."""
    if no_score and fail_under is not None:
        typer.echo("Error: --fail-under cannot be used together with --no-score.", err=True)
        raise typer.Exit(2)

    report = scan_project(path, include_score=not no_score, strict=strict)
    if output_format == OutputFormat.json:
        typer.echo(
            json.dumps(
                report.to_dict(include_score=not no_score, include_explanation=explain),
                indent=2,
                sort_keys=True,
            )
        )
        _exit_if_under_threshold(report.score, fail_under)
        return
    if output_format == OutputFormat.markdown:
        typer.echo(render_markdown_report(report, include_score=not no_score))
        _exit_if_under_threshold(report.score, fail_under)
        return
    render_text_report(report, include_score=not no_score, explain=explain)
    _exit_if_under_threshold(report.score, fail_under)


@app.command("scan-url")
def scan_url(
    url: RepoUrlArgument,
    branch: BranchOption = None,
    no_score: NoScoreOption = False,
    explain: ExplainOption = False,
    output_format: FormatOption = OutputFormat.text,
    strict: StrictOption = False,
    fail_under: FailUnderOption = None,
) -> None:
    """Download a public GitHub repository ZIP temporarily and scan it."""
    if no_score and fail_under is not None:
        typer.echo("Error: --fail-under cannot be used together with --no-score.", err=True)
        raise typer.Exit(2)

    try:
        with prepare_remote_repository(url, branch=branch) as remote:
            report = scan_project(remote.path, include_score=not no_score, strict=strict)
    except RemoteScanError as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(2) from error

    _render_report(report, include_score=not no_score, explain=explain, output_format=output_format)
    _exit_if_under_threshold(report.score, fail_under)


def _render_report(
    report,
    *,
    include_score: bool,
    explain: bool,
    output_format: OutputFormat,
) -> None:
    if output_format == OutputFormat.json:
        typer.echo(
            json.dumps(
                report.to_dict(include_score=include_score, include_explanation=explain),
                indent=2,
                sort_keys=True,
            )
        )
        return
    if output_format == OutputFormat.markdown:
        typer.echo(render_markdown_report(report, include_score=include_score))
        return
    render_text_report(report, include_score=include_score, explain=explain)


def _exit_if_under_threshold(score: int | None, fail_under: int | None) -> None:
    if fail_under is not None and score is not None and score < fail_under:
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
