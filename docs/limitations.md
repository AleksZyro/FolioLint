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
- `scan-url` stores the downloaded ZIP and extracted repository in the operating system's temporary folder and removes that temporary folder after the scan.
- `scan-url` tries the `main` branch first, then `master`. Use `--branch` for a different branch.
- `scan-url` stops ZIP downloads above 50 MB by default to protect disk space. Use `--max-download-mb` for larger repositories.
- ZIP downloads are not full Git clones, so Git-aware hygiene checks are less precise for `scan-url` than for local Git repositories.
- Project type detection is intentionally conservative. It uses common files such as `pyproject.toml`, `package.json`, `vite.config.*` and HTML entrypoints; it does not understand every custom framework or build setup.
- Report export writes the generated result to a local file. FolioLint does not upload the report anywhere or modify the scanned repository.
- Baselines compare the stored score and category results only. They do not prove that the code or documentation improved in a meaningful way.
- New baselines store a schema version and repository provenance when it is available. FolioLint refuses comparisons where both identities differ, but it cannot verify identity for legacy baselines or local folders without Git metadata.
- The GitHub Actions example installs FolioLint from the configured package source. CI therefore needs internet access even though local `scan PATH` does not.
- The example pins the FolioLint commit and direct package versions. A fully hash-locked dependency mirror is outside the current MVP scope.
