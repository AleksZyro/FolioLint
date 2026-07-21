# Limitations

FolioLint is intentionally small, local and rule-based.

- README checks are heuristics. The tool searches for common words and hints, but it does not really understand whether the README is clear, honest or useful.
- The secret check is not a real security scanner. It only detects obvious risky assignment names and private-key block markers.
- The score is not a judgement about code quality. It only estimates how ready the repository looks for public presentation.
- Not every project needs screenshots or a demo. Libraries, learning notes or backend tools can still be useful without visual media.
- Some projects should stay private on purpose. A higher score does not mean a repository should be published.
- The tool cannot fully understand context, project goals, legal constraints or personal boundaries.
- Warnings can be false positives. See [warnings.md](warnings.md) for examples of when a warning may be safe to ignore.
- `scan-url` needs internet access to download the repository ZIP file.
- `scan-url` supports public GitHub repositories only. It does not use a GitHub API key and does not support private repositories.
- `scan-url` tries the `main` branch first, then `master`. Use `--branch` for a different branch.
- ZIP downloads are not full Git clones, so Git-aware hygiene checks are less precise for `scan-url` than for local Git repositories.
