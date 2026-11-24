# Änderungen

## 1.0.1 – 24.11.2026

Nur die Modelliste im Browser betroffen, am Server und an den API-Pfaden ändert
sich nichts.

- **Überholte Modellantworten werden verworfen.** Bisher schrieb jede Antwort
  von `/api/modelle` in dieselbe Liste: Wer während einer langsamen Abfrage den
  Endpunkt wechselte, konnte die Modelle des alten Endpunkts unter dem neuen
  sehen, und ein spät eintreffender Fehler leerte die aktuelle Liste. Jede
  Ladung zählt jetzt eine laufende Nummer hoch; Antwort und Fehler älterer
  Anfragen werden still verworfen. Zusätzlich wird die vom Server mitgelieferte
  Endpunkt-Kennung geprüft.

## 1.00 – 17.11.2026

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
- **Sprachumschalter** (EN / DE) oben rechts; alle Texte liegen als Schlüssel
  in `static/app.js` (`TEXTE`), das HTML trägt `data-i18n`-Attribute.
- **Helles und dunkles Design** mit Sonne/Mond-Schalter; ohne eigene Wahl gilt
  die Systemeinstellung (`prefers-color-scheme`), beide Wahlen bleiben im
  Browser.
- Reines Python 3 (Standardbibliothek), keine Abhängigkeiten, kein venv.
- Lizenz **AGPL-3.0-or-later** – `LICENSE` enthält den vollständigen Text.
- Paketbau (`paket-bauen.sh`) und Ein-Zeilen-Installation aus dem eigenen Netz
  (`get.sh`).

### Umbenennung

Bis 17.11.2026 hieß das Werkzeug `ollama-sort`. Verzeichnis, Programm und
Kurzbefehl heißen jetzt `ollamaskope`; die alten Konfigurationsdateien
`ollama-sort.conf` / `ollama-sort.env` und die Umgebungsvariablen
`OLLAMA_SORT_*` werden weiter gelesen.
