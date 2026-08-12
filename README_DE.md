# FolioLint

[English](README.md) | **Deutsch**

FolioLint ist ein lokales Python-CLI für GitHub-Portfolio-Checks. Es prüft, ob ein Repository vor einer öffentlichen Präsentation sauber genug vorbereitet ist: README, Installation, Nutzung, Tests, Lizenz, Screenshots, Demo-Hinweise, Repository-Hygiene, grosse Dateien und offensichtliche Secret-Risiko-Hinweise.

## Welches Problem löst FolioLint?

Viele Portfolio-Repositories funktionieren technisch, wirken aber für Recruiter oder Reviewende unfertig: keine klare README, keine Setup-Schritte, keine Tests erwähnt, fehlende Lizenz, keine Screenshots oder unklare Demo. FolioLint macht daraus eine wiederholbare lokale Checkliste mit transparentem Score.

FolioLint ersetzt keine Code-Review und keinen echten Security-Scan. Es hilft dabei, langweilige, aber wichtige Präsentationsprobleme zu finden, bevor ein Projekt öffentlich geteilt wird.

## Wobei hilft es?

- README-Lücken sichtbar machen
- fehlende Installation, Nutzung oder Test-Hinweise finden
- Lizenz-, Screenshot- und Demo-Hinweise prüfen
- grosse Dateien, `.env`-Dateien und Logs erkennen
- offensichtliche Secret-Risiko-Wörter markieren
- lokale und öffentliche GitHub-Repositories prüfen
- Markdown- oder JSON-Ausgabe für CI, Issues oder Dokumentation erzeugen

## Installation

Voraussetzungen:

- Python `3.11` oder neuer
- Git, wenn du das Repository klonen willst

Windows PowerShell:

```powershell
git clone https://github.com/AleksZyro/FolioLint.git
cd FolioLint
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

macOS oder Linux:

```bash
git clone https://github.com/AleksZyro/FolioLint.git
cd FolioLint
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Nutzung

Lokales Repository prüfen:

```bash
foliolint scan .
foliolint scan . --explain
foliolint scan . --format markdown
foliolint scan . --fail-under 75
```

Öffentliches GitHub-Repository prüfen:

```bash
foliolint scan-url https://github.com/AleksZyro/FolioLint --explain
foliolint scan-url https://github.com/OWNER/REPO --format json
```

`scan PATH` arbeitet lokal und braucht keinen Internetzugang. `scan-url URL` lädt ein öffentliches GitHub-Repository temporär als ZIP herunter, prüft es lokal und löscht die temporären Dateien danach wieder.

## Beispiel

```text
FolioLint

Path: .
Score: 74/100
Status: Needs polish

Category          Status       Notes
README            OK           Purpose, setup and usage found
License           Warning      No LICENSE file found
Tests             OK           pytest tests detected
Media             Warning      No screenshots or demo media found
```

## Qualitätssicherung

```bash
python -m pytest
python -m ruff check .
python -m ruff format --check .
```

## Grenzen

- FolioLint versteht den vollständigen Projektkontext nicht.
- Der Score ist ein Showcase-Readiness-Score, kein objektiver Qualitätswert.
- Die Secret-Hinweise sind einfache Heuristiken und ersetzen keinen professionellen Secret-Scan.
- Das Tool bearbeitet README oder Lizenz nicht automatisch.

## Tech-Stack

- Python
- Typer
- Rich
- pytest
- Ruff

## Repository-Metadaten Vorschlag

- Description: `Local Python CLI for GitHub portfolio linting and repository showcase readiness checks.`
- Topics: `python`, `cli`, `portfolio`, `github`, `readme`, `linter`, `repository-hygiene`, `showcase-readiness`

## Lizenz

MIT-Lizenz. Details stehen in [LICENSE](LICENSE).
