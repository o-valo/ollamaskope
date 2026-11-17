# Änderungen

## 0.1.0 – 17.11.2026

Erste veröffentlichte Fassung.

- Modelliste eines oder mehrerer Ollama-Endpunkte im Browser: anzeigen,
  Modelfile bauen, Modell erzeugen, ausrollen, löschen.
- **Laden / Entladen** je Modellzeile (`keep_alive` 30 min bzw. 0) – das
  Gegenstück zu `ollama run` und `ollama stop`.
- Jeder Lade- und Entladeversuch landet in `laden.log`: Zeit, Aktion, Endpunkt,
  URL, Modell, Dauer und `done_reason`; Fehlschläge als `fehler: …`.
- Endpunkte im Web eintragen und entfernen, mit Prüfung der URL vor dem
  Speichern.
- Zwei Konfigurationswege: `config.json` und die zeilenweise
  `ollamaskope.conf` (Vorrang, unbekannte Schlüssel sind ein Fehler mit
  Zeilennummer).
- Rechte je Endpunkt: `schreiben: false` sperrt Erzeugen, Ausrollen und Löschen.
- Reines Python 3 (Standardbibliothek), keine Abhängigkeiten, kein venv.
- Paketbau (`paket-bauen.sh`) und Ein-Zeilen-Installation aus dem eigenen Netz
  (`get.sh`).

### Umbenennung

Bis 17.11.2026 hieß das Werkzeug `ollama-sort`. Verzeichnis, Programm und
Kurzbefehl heißen jetzt `ollamaskope`; die alten Konfigurationsdateien
`ollama-sort.conf` / `ollama-sort.env` und die Umgebungsvariablen
`OLLAMA_SORT_*` werden weiter gelesen.
