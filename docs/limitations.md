# Limitations

FolioLint is intentionally small, local and rule-based.

- README checks are heuristics. The tool searches for common words and hints, but it does not really understand whether the README is clear, honest or useful.
- The secret check is not a real security scanner. It only detects obvious risky assignment names and private-key block markers.
- The score is not a judgement about code quality. It only estimates how ready the repository looks for public presentation.
- Not every project needs screenshots or a demo. Libraries, learning notes or backend tools can still be useful without visual media.
- Some projects should stay private on purpose. A higher score does not mean a repository should be published.
- The tool cannot fully understand context, project goals, legal constraints or personal boundaries.
