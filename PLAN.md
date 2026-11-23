# FolioLint – Wartungsplan

1. Scanpfade, Git-Aufrufe, Dateizugriffe und die Behandlung von Symlinks anhand des Codes und der vorhandenen Tests prüfen.
2. Bewertung, Profile, Konfiguration, Baselines und Ausgabeformate mit dem CLI-Verhalten abgleichen.
3. Englischen Einstieg und deutsche Übersetzung auf typische Befehle, Bewertung, Konfiguration und Grenzen konzentrieren.
4. Paket isoliert installieren, Tests und Linting ausführen sowie den installierten CLI-Einstieg und Paketbau prüfen.

Vor dem Commit `pytest -q` und `ruff check src tests` ausführen und ihre Anwendbarkeit dokumentieren. Nur geprüfte Projektdateien aufnehmen. Dateien unter `data/` vom Commit ausschliessen. Den Entwicklungsbranch pushen. Der Merge bleibt eine separate Entscheidung.
