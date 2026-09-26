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

<details open>
<summary>Installation mit Windows PowerShell</summary>

```powershell
git clone https://github.com/AleksZyro/FolioLint.git
cd FolioLint
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

</details>

<details>
<summary>Installation mit macOS oder Linux</summary>

```bash
git clone https://github.com/AleksZyro/FolioLint.git
cd FolioLint
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

</details>

## Nutzung

Lokales Repository prüfen:

```bash
foliolint scan .
foliolint scan . --explain
foliolint scan . --format markdown
foliolint scan . --fail-under 75
foliolint scan . --format markdown --output report.md
foliolint init
foliolint scan . --format html --output report.html
```

<details open>
<summary>Öffentliches GitHub-Repository prüfen</summary>

```bash
foliolint scan-url https://github.com/AleksZyro/FolioLint --explain
foliolint scan-url https://github.com/OWNER/REPO --format json
```

`scan PATH` arbeitet lokal und braucht keinen Internetzugang. `scan-url URL` lädt ein öffentliches GitHub-Repository temporär als ZIP herunter, prüft es lokal und löscht die temporären Dateien danach wieder.

Mit `--output PATH` kannst du einen Text-, JSON-, Markdown- oder HTML-Report als Datei speichern. `foliolint init` erstellt eine kommentierte Beispielkonfiguration und überschreibt keine bestehende `.foliolint.toml`.

Mit HTML-Reports kannst du das Ergebnis lokal im Browser öffnen. Die Datei wird nicht hochgeladen.

## Manuelle Checks gegen echte Repositories

Die automatisierte Testsuite braucht kein Internet. Wenn Internetzugang vorhanden ist, kannst du
die optionalen Smoke-Checks aus [docs/real-repository-checks.md](docs/real-repository-checks.md)
gegen öffentliche Repositories wie FolioLint, PathLab oder SortLab ausführen. Diese Checks sind
manuell und gehören bewusst nicht zur normalen CI.

Für einen Vergleich über die Zeit:

```text
foliolint scan . --save-baseline .foliolint-baseline.json
foliolint scan . --compare-baseline .foliolint-baseline.json --format markdown
```

Neue Baselines enthalten eine Schemaversion und die Repository-Herkunft. Lokale Git-Scans speichern
wenn verfügbar die normalisierte `origin`-Remote; `scan-url` speichert die öffentliche Quell-URL und
den Branch. FolioLint verweigert einen Vergleich, wenn beide Identitäten vorhanden sind und nicht
übereinstimmen. Ältere Baselines und lokale Ordner ohne Git-Metadaten bleiben vergleichbar, werden
aber als nicht verifiziert gekennzeichnet.

</details>

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

<details>
<summary>Qualitätssicherung</summary>

```bash
python -m pytest
python -m ruff check .
python -m ruff format --check .
```

</details>

## Grenzen

- FolioLint versteht den vollständigen Projektkontext nicht.
- Der Score ist ein Showcase-Readiness-Score, kein objektiver Qualitätswert.
- Die Secret-Hinweise sind einfache Heuristiken und ersetzen keinen professionellen Secret-Scan.
- Das Tool bearbeitet README oder Lizenz nicht automatisch.
- Häufige Projekttypen wie Python, Node, React, Vite und statische Websites werden grob erkannt.

## Tech-Stack

- Python
- Typer
- Rich
- pytest
- Ruff

## GitHub Actions

Eine fertige Workflow-Vorlage steht unter [docs/examples/foliolint.yml](docs/examples/foliolint.yml). Kopiere sie in deinem Repository nach `.github/workflows/foliolint.yml`, damit FolioLint bei Pushes und Pull Requests läuft.

<details>
<summary>Repository-Metadaten Vorschlag</summary>

- Description: `Local Python CLI for GitHub portfolio linting and repository showcase readiness checks.`
- Topics: `python`, `cli`, `portfolio`, `github`, `readme`, `linter`, `repository-hygiene`, `showcase-readiness`

</details>

## Lizenz

MIT-Lizenz. Details stehen in [LICENSE](LICENSE).
