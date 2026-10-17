"""Public compatibility facade for built-in checks and the ordered registry."""

from foliolint.check_metadata import (
    DEMO_CHECK_ID as DEMO_CHECK_ID,
)
from foliolint.check_metadata import (
    HYGIENE_CHECK_ID as HYGIENE_CHECK_ID,
)
from foliolint.check_metadata import (
    LICENSE_CHECK_ID as LICENSE_CHECK_ID,
)
from foliolint.check_metadata import (
    MEDIA_CHECK_ID as MEDIA_CHECK_ID,
)
from foliolint.check_metadata import (
    METADATA_CHECK_ID as METADATA_CHECK_ID,
)
from foliolint.check_metadata import (
    README_CHECK_ID as README_CHECK_ID,
)
from foliolint.check_metadata import (
    SECRETS_CHECK_ID as SECRETS_CHECK_ID,
)
from foliolint.check_metadata import (
    TESTS_CHECK_ID as TESTS_CHECK_ID,
)
from foliolint.checks.demo import check_demo as check_demo
from foliolint.checks.hygiene import check_hygiene as check_hygiene
from foliolint.checks.license import check_license as check_license
from foliolint.checks.media import check_media as check_media
from foliolint.checks.metadata import check_metadata as check_metadata
from foliolint.checks.project_type import detect_project_type as detect_project_type
from foliolint.checks.readme import check_readme as check_readme
from foliolint.checks.registry import CHECK_REGISTRY as CHECK_REGISTRY
from foliolint.checks.registry import run_checks as run_checks
from foliolint.checks.secrets import check_secrets as check_secrets
from foliolint.checks.tests import check_tests as check_tests
