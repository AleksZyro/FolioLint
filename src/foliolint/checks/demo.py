from __future__ import annotations

import re
from pathlib import Path

from foliolint.check_metadata import DEMO
from foliolint.checks.common import _has_any_term, _read_text
from foliolint.config import ShowcaseConfig
from foliolint.models import CheckResult


def check_demo(path: Path, config: ShowcaseConfig) -> CheckResult:
    del config
    readme_text = _read_text(path / "README.md").lower()
    hosted_demo = bool(
        re.search(r"https?://[^\s)]+(netlify\.app|vercel\.app|github\.io)", readme_text)
    )
    local_demo = _has_any_term(
        readme_text,
        [
            "127.0.0.1",
            "localhost",
            "npm run dev",
            "npm start",
            "python -m http.server",
            "streamlit run",
            "uvicorn",
            "flask run",
            "typer",
            "foliolint scan",
        ],
    )
    python_module_demo = any(
        match.group("module").split(".", maxsplit=1)[0] not in NON_DEMO_PYTHON_MODULES
        for match in PYTHON_MODULE_RE.finditer(readme_text)
    )
    local_demo = local_demo or python_module_demo
    found = hosted_demo or local_demo
    if found:
        message = "Hosted demo link found." if hosted_demo else "Local start instructions found."
        explanation = "Demo gets 10/10 because hosted or local demo instructions were found."
        recommendations = []
    else:
        message = "No demo link or local start path found."
        explanation = (
            "Demo gets 0/10 because README.md has no hosted demo link or local start instruction."
        )
        recommendations = [
            "Document a hosted demo link or a local start command when the project supports it."
        ]
    return CheckResult(
        category=DEMO.category,
        status="ok" if found else "warning",
        message=message,
        points=DEMO.max_points if found else 0,
        max_points=DEMO.max_points,
        details={"hosted_demo": hosted_demo, "local_demo": local_demo},
        explanation=explanation,
        recommendations=recommendations,
    )


PYTHON_MODULE_RE = re.compile(r"\bpython(?:3(?:\.\d+)?)?\s+-m\s+(?P<module>[A-Za-z_][\w.]*)")


NON_DEMO_PYTHON_MODULES = {"coverage", "pip", "pytest", "unittest"}
