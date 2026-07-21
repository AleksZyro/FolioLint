from foliolint.models import CheckResult
from foliolint.scoring import apply_strict_mode, calculate_score, score_status


def test_score_status_bands() -> None:
    assert score_status(49) == "Not ready"
    assert score_status(50) == "Needs polish"
    assert score_status(75) == "Almost showcase-ready"
    assert score_status(90) == "Showcase-ready"


def test_calculate_score_normalises_to_100() -> None:
    checks = [
        CheckResult("A", "ok", "ok", 5, 10),
        CheckResult("B", "ok", "ok", 5, 10),
    ]

    assert calculate_score(checks) == 50


def test_strict_mode_deducts_for_missing_ci() -> None:
    checks = [
        CheckResult(
            "Tests",
            "ok",
            "tests",
            10,
            15,
            details={"github_actions": False},
            explanation="Tests gets 10/15.",
        )
    ]

    strict = apply_strict_mode(checks)

    assert strict[0].points == 7
    assert "Strict mode" in strict[0].explanation

