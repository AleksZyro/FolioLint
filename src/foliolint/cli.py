from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer

from foliolint.report import render_text_report
from foliolint.scanner import scan_project


class OutputFormat(StrEnum):
    text = "text"
    json = "json"


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
) -> None:
    """Scan a repository path."""
    report = scan_project(path, include_score=not no_score, strict=strict)
    if output_format == OutputFormat.json:
        typer.echo(
            json.dumps(
                report.to_dict(include_score=not no_score, include_explanation=explain),
                indent=2,
                sort_keys=True,
            )
        )
        return
    render_text_report(report, include_score=not no_score, explain=explain)


if __name__ == "__main__":
    app()
