# Scoring

FolioLint uses a transparent 0-100 readiness score. The score means public showcase readiness, not general code quality, hiring value or project importance.

Every point comes from a rule-based check:

| Category | Max points | What earns points |
| --- | ---: | --- |
| README | 25 | README.md exists, project purpose, setup, usage, tests, status or limitations, screenshot or demo hints |
| License | 10 | LICENSE, LICENCE or COPYING exists |
| Tests | 15 | tests folder, Python test files, package.json test script, GitHub Actions workflow |
| Media | 10 | Screenshot or demo media in docs/assets, assets, public or referenced in README |
| Demo | 10 | Hosted demo link or local start instruction in README |
| Hygiene | 15 | Starts at full points, deducts for generated folders, large files, .env files and log files |
| Secrets | 10 | No obvious secret risk strings found |
| Metadata | 5 | pyproject.toml, requirements.txt, package.json, vite.config.* or .github/workflows |

Status bands:

| Score | Status |
| --- | --- |
| 0-49 | Not ready |
| 50-74 | Needs polish |
| 75-89 | Almost showcase-ready |
| 90-100 | Showcase-ready |

Strict mode keeps the same categories but deducts extra points for incomplete README hints, missing GitHub Actions in the test category and repository hygiene warnings. It is meant for projects that should be easier to review publicly.

Use `--explain` to see the points per category. Use `--no-score` when a checklist-style output is better than a number.

