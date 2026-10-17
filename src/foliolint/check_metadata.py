"""Stable check identities and scoring metadata, independent of runners and the CLI."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

MEDIA_LIGHT_PROJECT_TYPES = frozenset(
    {
        "cli",
        "library",
        "learning-project",
        "local-app",
        "local-tool",
        "node-cli",
        "python-cli",
    }
)


@dataclass(frozen=True)
class CheckMetadata:
    id: str
    category: str
    description: str
    max_points: int
    ignorable: bool = True
    project_type_max_points: Mapping[str, int] = field(default_factory=lambda: MappingProxyType({}))

    @property
    def scored(self) -> bool:
        return self.max_points > 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "category": self.category,
            "description": self.description,
            "max_points": self.max_points,
            "scored": self.scored,
            "ignorable": self.ignorable,
            "project_type_max_points": dict(self.project_type_max_points),
        }


_MEDIA_CAPS = MappingProxyType(dict.fromkeys(sorted(MEDIA_LIGHT_PROJECT_TYPES), 5))
README = CheckMetadata("readme", "README", "README purpose, setup, usage and limits", 25)
LICENSE = CheckMetadata("license", "License", "License file presence", 10)
TESTS = CheckMetadata("tests", "Tests", "Test files and test workflow hints", 15)
MEDIA = CheckMetadata(
    "media", "Media", "Screenshot or demo media hints", 10, project_type_max_points=_MEDIA_CAPS
)
DEMO = CheckMetadata(
    "demo-link",
    "Demo",
    "Hosted demo or local start instructions",
    10,
    project_type_max_points=_MEDIA_CAPS,
)
HYGIENE = CheckMetadata("hygiene", "Hygiene", "Generated, large, environment and log files", 15)
SECRETS = CheckMetadata("secrets", "Secrets", "Obvious secret risk hints (not a security scan)", 10)
METADATA = CheckMetadata("metadata", "Metadata", "Common project and workflow metadata", 5)

CHECK_METADATA = (README, LICENSE, TESTS, MEDIA, DEMO, HYGIENE, SECRETS, METADATA)
METADATA_BY_CATEGORY = MappingProxyType({check.category: check for check in CHECK_METADATA})

# Compatibility names for existing users of foliolint.checks.
README_CHECK_ID = README.id
LICENSE_CHECK_ID = LICENSE.id
TESTS_CHECK_ID = TESTS.id
MEDIA_CHECK_ID = MEDIA.id
DEMO_CHECK_ID = DEMO.id
HYGIENE_CHECK_ID = HYGIENE.id
SECRETS_CHECK_ID = SECRETS.id
METADATA_CHECK_ID = METADATA.id
