# Scoring

FolioLint uses a transparent 0-100 readiness score. The score means public showcase readiness, not general code quality, hiring value or project importance.

Every point comes from a rule-based check:

| Category | Max points | What earns points |
| --- | ---: | --- |
| README | 25 | README.md exists, project purpose, setup, usage, tests, status or limitations, screenshot or demo hints. Headings and code blocks can count as evidence |
| License | 10 | LICENSE, LICENCE or COPYING exists |
| Tests | 15 | tests folder, Python or common JS/TS test files, package.json test script, GitHub Actions workflow with test or lint commands |
| Media | 10 | Screenshot or demo media in docs/assets, assets, public or referenced in README |
| Demo | 10 | Hosted demo link or local start instruction in README |
| Hygiene | 15 | Starts at full points, deducts for tracked generated folders, large files, .env files and log files |
| Secrets | 10 | No obvious secret risk strings found |
| Metadata | 5 | pyproject.toml, requirements.txt, package.json, vite.config.* or workflow files |

Status bands:

| Score | Status |
| --- | --- |
| 0-49 | Not ready |
| 50-74 | Needs polish |
| 75-89 | Almost showcase-ready |
| 90-100 | Showcase-ready |

Strict mode keeps the same categories but deducts extra points for incomplete README hints, missing GitHub Actions in the test category and repository hygiene warnings. It is meant for projects that should be easier to review publicly.

Project type can adjust category weight when configured in `.foliolint.toml`.

| Project type | Adjustment |
| --- | --- |
| `web-app` | Uses the default weighting. Demo and media checks stay important. |
| `local-app` | Uses the default weighting. |
| `cli` | Media and Demo are capped at 5 points each. |
| `library` | Media and Demo are capped at 5 points each. |
| `learning-project` | Media and Demo are capped at 5 points each. |

The adjustment is intentionally small. It reduces noisy warnings for projects where screenshots or hosted demos are less central, but it does not remove the checks.

Use `--explain` to see the points per category. Use `--no-score` when a checklist-style output is better than a number.

Use `--details` to show the files, patterns or workflow hints behind checks. This helps review false positives without making the default output noisy.

`--fail-under N` exits with code 1 when the score is below `N`. This is intended for local CI checks, not as a universal quality gate.

Exit codes:

| Code | Meaning |
| ---: | --- |
| 0 | Scan completed. |
| 1 | Scan completed, but the score was below `--fail-under`. |
| 2 | Invalid input, unsupported URL or remote download problem. |

FolioLint uses `git ls-files` in Git repositories to focus hygiene warnings on tracked files. If Git is not available or the scanned folder is not a Git repository, FolioLint falls back to `.gitignore` heuristics.
