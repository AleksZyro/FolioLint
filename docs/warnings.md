# Understanding Warnings

FolioLint warnings are review prompts, not automatic failures. A warning means "check this before sharing", not "the project is bad".

## README Warnings

README checks use simple keyword hints. A warning can be reasonable to ignore when:

- The repository is a small code sample with context explained somewhere else.
- The project is an internal exercise and does not need a full public README.
- Setup or usage is obvious from a single file, but not written with common keywords.
- The project is intentionally archived and no longer meant to be polished.

If the project is meant for Reddit, a portfolio or a public profile, a short README with purpose, setup, usage and limits is still recommended.

## Media Warnings

Not every project needs screenshots or video. A warning can be reasonable to ignore when:

- The project is a library, package or backend tool.
- The result is not visual.
- The README already explains the behaviour clearly with commands and output.

Screenshots help most for games, dashboards, UI projects and visual tools.

## Demo Warnings

A hosted demo is not always needed. A warning can be reasonable to ignore when:

- The project is a local CLI.
- Running a demo would require private services or paid resources.
- The README contains enough commands to reproduce the behaviour locally.

For local tools, a short command such as `foliolint scan . --no-score` is often enough.

## Hygiene Warnings

Generated folders, cache folders and logs often appear during local development. A warning can be reasonable to ignore when:

- The files are ignored by git and only exist in the local working tree.
- The files are intentional fixtures for tests.
- Large demo media is intentionally stored in the repository and explained.

Before public sharing, check what is actually tracked by git.

## Secret-Risk Warnings

The secret-risk check only looks for obvious assignment-style hints in normal project files. It skips common generated and dependency folders to reduce noise.

A warning can be a false positive when:

- A test fixture contains fake credentials.
- Documentation intentionally shows placeholder names.
- The value is clearly not a real secret.

Do not rely on FolioLint for security review. Use a dedicated secret scanner before publishing sensitive projects.

