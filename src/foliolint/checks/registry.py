"""Ordered built-in check registry. Order and IDs are part of the report contract."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from foliolint.check_metadata import (
    DEMO,
    HYGIENE,
    LICENSE,
    MEDIA,
    METADATA,
    README,
    SECRETS,
    TESTS,
    CheckMetadata,
)
from foliolint.checks.demo import check_demo
from foliolint.checks.hygiene import check_hygiene
from foliolint.checks.license import check_license
from foliolint.checks.media import check_media
from foliolint.checks.metadata import check_metadata
from foliolint.checks.readme import check_readme
from foliolint.checks.secrets import check_secrets
from foliolint.checks.tests import check_tests
from foliolint.config import ShowcaseConfig
from foliolint.models import CheckResult


@dataclass(frozen=True)
class RegisteredCheck:
    metadata: CheckMetadata
    run: Callable[[Path, ShowcaseConfig], CheckResult]


CHECK_REGISTRY = (
    RegisteredCheck(README, check_readme),
    RegisteredCheck(LICENSE, check_license),
    RegisteredCheck(TESTS, check_tests),
    RegisteredCheck(MEDIA, check_media),
    RegisteredCheck(DEMO, check_demo),
    RegisteredCheck(HYGIENE, check_hygiene),
    RegisteredCheck(SECRETS, check_secrets),
    RegisteredCheck(METADATA, check_metadata),
)


def run_checks(path: Path, config: ShowcaseConfig) -> list[CheckResult]:
    results = []
    ignored = set(config.ignore.checks)
    for check in CHECK_REGISTRY:
        meta = check.metadata
        if meta.ignorable and meta.id in ignored:
            results.append(
                CheckResult(
                    category=meta.category,
                    status="ignored",
                    message="Check ignored by configuration.",
                    points=0,
                    max_points=0,
                    explanation=f"The check id '{meta.id}' is listed in .foliolint.toml.",
                )
            )
        else:
            results.append(check.run(path, config))
    return results
