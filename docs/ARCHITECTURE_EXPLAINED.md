# FolioLint erklären und warten

FolioLint prüft, ob sich ein Repository gut als Portfolio-Projekt zeigen lässt.
Es sucht Hinweise auf eine verständliche README, eine Lizenz, Tests, eine Demo
und typische aufräumbare Dateien. Das Ergebnis enthält Befunde, konkrete
Empfehlungen und auf Wunsch einen Score. Für einen ersten Durchlauf:

~~~sh
foliolint scan . --explain --details
foliolint list-checks
~~~

## Vom Befehl zum Report

1. `cli.py` liest mit Typer den Pfad und die Optionen. `scan` prüft einen lokalen
   Ordner. `scan-url` bereitet zuerst eine temporäre lokale Kopie vor.
2. `scanner.py` lädt die Konfiguration und ruft `run_checks` auf. Die Checks liefern
   je ein `CheckResult` mit Status, Punkten, Details und Empfehlungen.
3. Der Scanner passt die Gewichtung an den Projekttyp an und wendet optional
   den Strict Mode an. Er fasst die Checks und bis zu acht unterschiedliche
   Empfehlungen in einem `ScanReport` zusammen.
4. Beide Scan-Befehle laufen in `_finish_scan` zusammen. Die CLI vergleicht oder
   speichert bei Bedarf eine Baseline und gibt den Report aus. Erst danach
   entscheidet `--fail-under`, ob der Prozess mit Code 1 endet.

Die Formatierung entscheidet nicht über Punkte. Derselbe Scan lässt sich als
Text, JSON, Markdown, HTML oder GitHub-Workflow-Ausgabe darstellen.

## Wo finde ich was?

| Datei unter `src/foliolint/` | Aufgabe |
| --- | --- |
| `cli.py` | Befehle, Optionen, Ausgabe, Exit-Codes und `init` für eine Beispielkonfiguration |
| `scanner.py` | Ablauf eines Scans vom Ordner zum Ergebnis |
| `models.py` | Daten für ein einzelnes Check-Ergebnis und den gesamten Scan; JSON-Felder |
| `scoring.py` | Projekttyp-Gewichtung, Strict Mode, Score und Statusstufen |
| `config.py` | `.foliolint.toml` lesen und Standardwerte bereitstellen |
| `baseline.py` | Ergebnisse als JSON speichern, laden, vergleichen und die Herkunft prüfen |
| `remote.py` | GitHub-URL prüfen, ZIP begrenzen, herunterladen, entpacken und aufräumen |
| `report.py` | Text mit Rich, Markdown und eigenständiges HTML aus Scan-Daten erzeugen |
| `github_report.py` | Warnungen als GitHub-Annotations ausgeben, wenn ein konkreter Dateibezug vorliegt |
| `check_metadata.py` | Stabile Check-IDs, Kategorien, Beschreibungen und Punktegrenzen |
| `checks/registry.py` | Geordnete Liste der Check-Funktionen und Ausführung mit Ignore-Regeln |
| `checks/common.py` | Gemeinsame Datei- und Textsuche |
| `checks/project_type.py` | Projekttyp aus Dateien wie `package.json` und `pyproject.toml` ableiten |
| `checks/__init__.py` | Bestehende Imports für Check-Funktionen, IDs und Registry bereitstellen |
| `__init__.py` | Paketversion |

Die restlichen Dateien unter `checks/` enthalten die eigentlichen Regeln:
`readme.py` (Abschnitte und Hinweise), `license.py` (Lizenzdatei), `tests.py`
(Testdateien und Workflow-Hinweise), `media.py` (Screenshots), `demo.py` (Startanleitung
oder Demo-Link), `hygiene.py` (zum Beispiel Logs und grosse Dateien), `secrets.py`
(verdächtige Muster) und `metadata.py` (Projektdateien und Workflow-Metadaten).

## Checks und Score

Die Registry verbindet jede Check-Funktion mit ihren Metadaten. Die Reihenfolge
ist fest, und `list-checks` liest dieselbe Liste. Eine Check-ID wie `demo-link`
ist der stabile Name für die Konfiguration. Die Kategorie `Demo` erscheint im
Report und dient beim Baseline-Vergleich als Schlüssel.

Jeder Check bekommt den Ordner und die Konfiguration. Steht seine ID in
`ignore.checks`, liefert die Registry direkt ein Ergebnis mit Status `ignored`
und null möglichen Punkten. Die Check-Funktion läuft dann nicht. `ignore.paths`
wirkt bei den Checks, die den gemeinsamen Datei-Walk verwenden. Ein direkter
Zugriff, etwa auf die README im Projektstamm, ist davon nicht generell betroffen.

Der Projekttyp kommt aus `project.type` oder wird erkannt. Bei Typen wie
`python-cli` oder `library` sinkt das Maximum für Media und Demo von je 10 auf
je 5 Punkte; auch die erhaltenen Punkte werden an dieser Grenze gekappt.
Strict Mode kann danach Punkte für eine unvollständige README, fehlende
Workflow-Hinweise oder Hygiene-Warnungen abziehen. Die Maxima bleiben dabei gleich.

Der Score ist `round(erhaltene Punkte / mögliche Punkte × 100)`, begrenzt auf
0 bis 100. Checks ohne mögliche Punkte zählen nicht mit. Wenn kein Check
Punkte beitragen kann, ist der Score 0. Beispiel: 54 von 90 möglichen Punkten
ergeben 60. `--no-score` lässt den Gesamtwert weg; die Checks laufen trotzdem.

## Remote-Scan, Konfiguration und Baseline

**Remote:** `scan-url` akzeptiert öffentliche GitHub-Repositories per HTTPS.
Ohne `--branch` versucht es zuerst `main` und dann `master`. Pro Versuch gibt es
einen eigenen temporären Ordner. Standardmässig sind der Download auf 50 MiB
und das Archiv auf 250 MiB entpackte Daten und 5000 Dateien begrenzt.
Vor dem Entpacken prüft FolioLint, ob die Zielpfade innerhalb des temporären
Ordners liegen. Der normale Scanner liest danach die entpackten Dateien.
Der `with`-Block räumt die Kopie auch bei einem Fehler auf. Repository-Code
wird nicht ausgeführt.

**Konfiguration:** Der Scanner liest `.foliolint.toml` aus dem Projektstamm.
Ohne Datei gelten die Standardwerte. `foliolint init` legt ein kommentiertes
Beispiel an und lässt eine vorhandene Datei stehen. Neben Ignore-Regeln kann
die Datei den Projekttyp und die Grössenschwelle für den Hygiene-Check festlegen.

**Baseline:** `--save-baseline` speichert Schema-Version, Score, Status und die
Punkte pro Kategorie. Wenn verfügbar, kommt die Herkunft dazu: lokal die
normalisierte Git-Origin-URL, bei Remote-Scans die URL und der Branch.
`--compare-baseline` zeigt hinzugefügte, entfernte oder veränderte Kategorien
und die Score-Differenz. Bei widersprüchlicher Herkunft verweigert FolioLint
den Vergleich. Fehlt die Herkunft, bleibt der Vergleich möglich und wird als
nicht verifiziert gekennzeichnet. Vergleichen verändert den aktuellen Score nicht.

## Warum der Code so aufgebaut ist

- Eine feste Registry reicht für acht eingebaute Checks. Es gibt kein dynamisches
  Plugin-System und keine automatische Suche nach Check-Klassen.
- Die Checks liefern Daten statt fertige Ausgaben. So können CLI, HTML-Report
  und GitHub-Annotations dieselben Ergebnisse verwenden.
- Lokal und remote wird derselbe Ordner-Scanner benutzt. Nur die Beschaffung
  der Dateien unterscheidet sich.
- Baselines sind einfache JSON-Dateien. Für einen Vergleich ist keine Datenbank
  und kein GitHub-Zugang nötig.

## Grenzen

FolioLint bewertet Hinweise, keine Codequalität. Eine gefundene Lizenzdatei
ist keine rechtliche Prüfung; gefundene Testdateien beweisen weder, dass Tests
laufen, noch dass sie gut sind. Der Secret-Check findet nur offensichtliche
Muster und ersetzt keinen Security-Scanner. Die README-Erkennung ist kein
vollständiger Markdown-Parser. Der Score ist eine Orientierung für die
Präsentation eines Projekts, kein objektives Urteil über das Projekt.

## Zehn Fragen fürs Bewerbungsgespräch

1. **Was macht FolioLint?** Es prüft Dateien eines Repositories auf Signale,
   die ein Portfolio-Projekt leichter verständlich und vorzeigbar machen.
2. **Wie ergänze ich einen Check?** Ich schreibe eine Funktion, die ein
   `CheckResult` liefert, definiere die Metadaten und trage beides in die Registry ein.
3. **Warum sind Check-ID und Kategorie getrennt?** Die ID bleibt als
   Konfigurationsschlüssel stabil; die Kategorie ist der Anzeigename und
   der bestehende Schlüssel im Baseline-Vergleich.
4. **Was passiert, wenn ich einen Check ignoriere?** Die Registry überspringt
   die Funktion. Das Ergebnis bleibt sichtbar, zählt aber nicht zum Score.
5. **Wie kommt der Score zustande?** Die erhaltenen Punkte werden durch die
   möglichen Punkte geteilt und auf eine Skala von 0 bis 100 umgerechnet.
6. **Was unterscheidet Projekttyp und Strict Mode?** Der Projekttyp kann
   Maximalpunkte ändern. Strict Mode zieht bei bestimmten Befunden Punkte ab.
7. **Was unterscheidet `scan` von `scan-url`?** `scan-url` lädt zuerst ein
   begrenztes ZIP, prüft es und entpackt es. Danach läuft derselbe Scanner.
8. **Wie funktioniert ein Baseline-Vergleich?** Er vergleicht Status und
   Punkte pro Kategorie mit der gespeicherten Datei und prüft, soweit möglich,
   ob beide Scans zum selben Repository gehören.
9. **Was bedeuten die Exit-Codes?** 0 bedeutet erfolgreich abgeschlossen,
   1 bedeutet unter `--fail-under`, und 2 steht beispielsweise für ungültige
   CLI-Optionen oder einen fehlgeschlagenen Remote-Scan.
10. **Wie bleiben die verschiedenen Ausgaben konsistent?** Der Scan erzeugt
    ein gemeinsames Datenmodell. Die Ausgabeformate zeigen diese Daten an,
    ohne den Score erneut zu berechnen.
