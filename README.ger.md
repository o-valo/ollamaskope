<p align="center">
  <img src="ollamaskope.jpg" alt="Ollamaskope V.1.0.0 " width="100%">
</p>

English: [README.md](README.md)

# Ollamaskope – Modelliste eines Ollama-Endpunkts als Web-Werkzeug

Zeigt die Modelle eines entfernten (oder lokalen) Ollama-Endpunkts, baut aus
jedem Modell ein portables Modelfile, erzeugt daraus ein neues Modell und
löscht Modelle. Reines Python 3 (Standardbibliothek), kein Flask, keine
Node-Abhängigkeiten – dasselbe Muster wie `~/wg-watcher/wg-http.py`.

Das Werkzeug rechnet nicht und läuft deshalb nicht auf einem Inferenz-Host. Es spricht nur die Ollama-API über HTTP.

## Installation

```bash
cd ~/ollamaskope
./install.sh                # prüfen und einrichten
./install.sh --start        # einrichten und gleich starten
./install.sh --check        # nur prüfen, nichts ändern
```

Der Installer prüft `python3` (mindestens 3.8) und `curl`, setzt die
Ausführungsrechte, legt `config.json` aus `config.example.json` an – eine
vorhandene `config.json` bleibt unangetastet – und schreibt den Kurzbefehl
`~/.local/bin/ollamaskope`, der `start|stop|restart|status` weiterreicht
(`--ohne-befehl` lässt ihn weg).

**Kein venv.** Das Werkzeug benutzt nur die Python-Standardbibliothek
(`http.server`, `urllib`, `json`, `threading`); ein venv wäre eine leere Hülle
mit einer zusätzlichen Fehlerquelle. Wenn später eine `requirements.txt`
auftaucht, legt `install.sh` `.venv` an und installiert sie; `ollamaskope.sh`
nimmt dann automatisch `.venv/bin/python` (`OLLAMASKOPE_OHNE_VENV=1` schaltet
das ab).

## Installation im LAN per curl

Läuft der Dienst auf einem Host im LAN, genügt auf einem anderen Rechner
eine Zeile – Paket und Installer kommen von dort:

```bash
curl -fsSL http://127.0.0.1:8090/get.sh | sh
```

Das Skript fragt, ob der Dienst nur lokal (`127.0.0.1`) oder im LAN
(`0.0.0.0`) lauschen soll, entpackt nach `~/ollamaskope`, ruft `install.sh`
auf und fragt am Ende, ob gestartet werden soll. Ohne Terminal (etwa aus
einem Skript) bleibt `config.json` unverändert und es wird nicht gestartet:

```bash
curl -fsSL http://127.0.0.1:8090/get.sh | sh -s -- --bind 0.0.0.0 --start
```

Optionen: `--bind 127.0.0.1|0.0.0.0`, `--quelle URL` (anderes Paket),
`--ziel PFAD`, `--start`, `--ohne-start`, `--hilfe`. Ein zweiter Lauf ist ein
Update: Programm und Oberfläche werden ersetzt, `config.json` und
`ollamaskope.conf` bleiben stehen.

Das Paket entsteht mit `./paket-bauen.sh` und liegt dann als
`static/ollamaskope.tar.gz` bereit (ohne `config.json`, PID-/Logdateien,
`.venv`). Nach Änderungen am Programm einmal neu bauen:

```bash
./paket-bauen.sh            # danach: curl …/get.sh | sh
```

## Start

```bash
cd ~/ollamaskope
./ollamaskope.sh start      # startet im Hintergrund, prüft /api/gesundheit
./ollamaskope.sh status
./ollamaskope.sh stop
```

Danach im Browser: **http://127.0.0.1:8090/**

Ohne Startskript (blockiert das Terminal):

```bash
python3 ollamaskope.py --port 8090
```

## Bedienung

| Schritt | Was passiert |
|---|---|
| Endpunkt wählen | Liste kommt von `/api/tags`, geladene Modelle werden markiert |
| **Modelfile** | `/api/show` wird zu einem bearbeitbaren Modelfile; „Als Datei“ speichert es als `Modelfile` |
| Namen eintragen, **Modell erzeugen** | `/api/create` läuft streamend, Fortschritt steht im Log |
| **Löschen** | erst wenn ein Modell geöffnet ist: Knopf am Modelfile-Editor und in der Abhängigkeitsübersicht; eine Nachfrage nennt das Modell, „Ja, löschen“ schickt `/api/delete` |
| **Ausrollen** | Modell öffnen, „⇄ Ausrollen“: Ziel-Endpunkt und Name wählen. Übertragen wird das Rezept (FROM, Parameter, Template, System), nicht die Gewichte – die Basis muss auf dem Ziel liegen oder auf Wunsch vorher gezogen werden |
| **Laden / Entladen** | je Zeile: lädt ein Modell in den Speicher (`keep_alive` 30 min) oder nimmt es heraus (`keep_alive` 0) – das Gegenstück zu `ollama run` |
| **Modell anklicken** | Übersicht: worauf es aufbaut, welche Modelle darauf aufbauen, Geschwister – mit „Dieses Modell löschen“ |
| **Spaltenkopf anklicken** | sortiert nach Modell, Größe, Familie, Parameterzahl, Quantisierung oder Änderungsdatum; zweiter Klick dreht um, dritter stellt die Server-Reihenfolge wieder her |
| **＋ Endpunkt** | neuen Endpunkt mit Name und URL eintragen (URL wird vorher geprüft) oder einen entfernen; beides landet in `config.json` |

Jeder Lade- und Entladeversuch landet zusätzlich in `laden.log` neben dem
Programm – eine Zeile je Versuch, mit Tabulatoren getrennt:

```text
2026-11-17T02:13:54	laden	fake	http://127.0.0.1:11434	klein:latest	1.84s	ok done_reason=load
```

Der Reihe nach: Zeit, Aktion (`laden`/`entladen`), Endpunktname, Endpunkt-URL,
Modell, Dauer, Ergebnis. Fehlschläge stehen als `fehler: …` darin – genau sie
beantworten später die Frage, warum ein 200 ankam und trotzdem nichts im
Speicher lag. Die Zugriffszeilen in `ollamaskope.log` sagen das nicht.

Die Aktionsknöpfe jeder Zeile stehen in der **ersten Spalte links**, vor dem
Modellnamen – bei schmalem Fenster bleiben sie sichtbar, ohne seitlich zu
scrollen. Die Modelfile-Karte klappt über ihre Überschrift auf und zu
(„▾ einklappen“ / „▸ ausklappen“); ein Klick auf „Modelfile“ in der Liste klappt
sie auf.

Beim Modelfile ersetzt das Werkzeug Blob-Pfade:

```text
FROM /usr/share/ollama/.ollama/models/blobs/sha256-…   ← so antwortet /api/show
FROM qwen-test:7b                                      ← so steht es im Editor
```

Für die Abhängigkeiten zählt dagegen **nicht** der Kommentar, sondern
`details.parent_model`: der `# FROM`-Hinweis nennt immer das Modell selbst
(„so baust du eine Kopie“). `GET /api/abhaengigkeiten?endpunkt=…&modell=…`
fragt `/api/show` für alle Modelle des Endpunkts parallel ab und antwortet mit
`baut_auf`, `darauf_bauen`, `geschwister` und `basis` (`modell`, `extern`,
`datei` oder `registry`). Das Ergebnis wird 120 s gehalten und nach Erzeugen
oder Löschen verworfen.

Ollama selbst schreibt den Hinweis `# FROM <name>` mit; er wird bevorzugt,
danach `details.parent_model`, zuletzt der Modellname. Ein zweites `FROM`
(Projektor) wird entfernt und als Hinweis angezeigt – `/api/create` nimmt nur
ein `FROM`.

## Modelle ausrollen

Ein Modell auf einem weiteren Endpunkt bereitstellen: Modell öffnen, „⇄ Ausrollen“,
Ziel und Namen wählen. Was dabei passiert, hängt davon ab, worauf das Modell
beruht – `details.parent_model` entscheidet (der `# FROM`-Kommentar nennt
immer das Modell selbst und taugt nicht):

| Fall | `parent_model` | Was das Werkzeug tut |
|---|---|---|
| aus der Registry geladen | leer | zieht dasselbe Modell auf dem Ziel (`/api/pull`) – das ergibt dieselben Gewichte. Anderer Zielname: danach `/api/copy` |
| aus einem anderen Modell gebaut | Modellname | `/api/create` mit `FROM <Elternteil>` plus Parameter, Template, System – die Gewichte kommen von der Basis, die auf dem Ziel liegen muss (Häkchen „Basis bei Bedarf ziehen“ lädt sie vorher) |
| aus einer GGUF-Datei gebaut | Dateiname | gesperrt, solange das Feature `gguf` aus ist (Standard). Freigeschaltet: `/api/create` aus einer GGUF, die **auf dem Ziel** liegt – kopiert wird nichts |

Ein Ausrollen überschreibt nie: ist der Zielname dort belegt, bricht das Werkzeug
mit einem Hinweis ab. Am 16.11.2026 an echten Endpunkten geprüft: auf ollama-3 baut
`codehamr-agent:latest` auf `Julioa/Qwen3.8-27B-UD-Q3_K_XL` auf (ausrollbar,
wo diese Basis liegt), `bonsai-2:27b` trägt `bonsai-2:27b-q2_0` als Elternteil,
und `qwen3.5:9b` hat gar keinen – das wird gezogen, nicht neu gebaut.

Bei einem Modell ohne Elternteil braucht das Ausrollen **keinen Zugriff auf die
Dateien der Quelle**: das Ziel zieht dasselbe Modell selbst aus der Registry und
bekommt damit dieselben Gewichte – vollständig, ohne SSH, ohne Blob-Kopie.

### GGUF-Modelle ausrollen (Feature, nicht Normalbetrieb)

Ist ein Modell aus einer GGUF-Datei gebaut, liegen seine Gewichte nur als Datei
vor – die API liefert sie nicht. Dieser Fall ist selten und deshalb
**standardmäßig gesperrt**; freigeschaltet wird er bewusst in der Konfiguration:

```json
{"gguf": true}
```

oder in `ollamaskope.conf`:

```text
gguf = ja
```

Dann baut das Werkzeug das Modell auf dem Ziel per `/api/create` aus einem
GGUF-Pfad, der **dort schon liegt** – kopiert wird nichts. Liegt die Datei auf
dem Ziel woanders, im Dialog unter „GGUF-Pfad auf dem Ziel“ eintragen. Fehlt sie
dort, antwortet Ollama mit seinem Fehler und das Werkzeug reicht ihn durch.

Gewichte wandern nie zwischen zwei Hosts: Ollama hat keinen Weg, Blobs
auszuliefern. Ohne Dateizugriff (SSH/scp, geteiltes Verzeichnis) lässt sich ein
aus einer GGUF-Datei gebautes Modell gar nicht bewegen.

## Konfiguration (`config.json`)

```json
{
  "bind": "127.0.0.1",
  "port": 8090,
  "timeout": 25,
  "endpunkte": [
    {"id": "ollama-1", "name": "ollama-1 (10.0.0.24)",
     "url": "http://10.0.0.24:11434", "schreiben": true}
  ]
}
```

* `schreiben: false` sperrt Erzeugen und Löschen für diesen Endpunkt; die
  Oberfläche deaktiviert die Knöpfe, der Server antwortet mit 403.
* Voreingestellt schreibgeschützt: **ollama-2** (dort bleibt ein Modell dauerhaft
  geladen, Löschen würde dort laufende Arbeit brechen) und **ollama-3** (dort laufen
  laufende Experimente).
* `bind: 0.0.0.0` nur bewusst setzen: es gibt **keine Anmeldung**.
* `"gguf": true` schaltet das Ausrollen aus GGUF-Dateien frei – Vorgabe ist
  aus, weil das ein Sonderfall ist und keine Grundeinstellung (siehe unten).

## Einfache Konfiguration (`ollamaskope.conf`)

Wer keine JSON-Datei pflegen will, legt daneben eine zeilenweise Datei an –
`ollamaskope.conf` oder `ollamaskope.env`, gleicher Aufbau:

```text
# Kommentar, Leerzeilen zählen nicht
bind = 0.0.0.0
port = 8090
timeout = 25

# name | url | rechte      (rechte: schreiben oder lesen)
endpunkt = ollama-1 | http://10.0.0.24:11434 | schreiben
endpunkt = ollama-2    | http://10.0.0.81:11434 | lesen
endpunkt = http://10.0.0.79:11434        # Name kommt aus der Adresse
```

* `=` oder `:` trennen Schlüssel und Wert; `OLLAMASKOPE_BIND=…` wird ebenso
  verstanden. Unbekannte Schlüssel sind ein Fehler **mit Zeilennummer** – nichts
  wird stillschweigend ignoriert.
* Reihenfolge der Suche: `--einfach PFAD`, dann `$OLLAMASKOPE_EINFACH`, sonst
  `ollamaskope.conf` bzw. `ollamaskope.env` neben `config.json`.
* **Diese Datei hat Vorrang.** Ihre Werte überschreiben `bind`, `port` und
  `timeout`; ihre Endpunkte stehen vorn. Endpunkte aus `config.json` kommen
  hinzu, solange ihre URL nicht schon in der einfachen Datei steht.
* Endpunkte aus der Datei sind im Web-Dialog mit „aus ollamaskope.conf“
  markiert und dort **nicht** entfernbar – sie gehören in die Datei. Neue
  Endpunkte aus dem Web landen weiterhin in `config.json`; beim Speichern
  werden die Datei-Endpunkte nicht hineingeschrieben (keine Doppelung).
* Prüfen ohne Start: `python3 ollamaskope.py --pruefen` (zeigt Quelle, Bind,
  Port und jeden Endpunkt mit Rechten; Exit 3 bei Fehler).

## Warum das Modelfile zerlegt wird

Ollama 0.40.14 nimmt das früher übliche Feld `modelfile` nicht mehr an. Probe
vom 16.11.2026 gegen `10.0.0.24` – alle drei Varianten antworten:

```json
{"error":"neither 'from' or 'files' was specified"}
```

Deshalb zerlegt `ollamaskope.py` den Text selbst und sendet `model`, `from`,
`parameters`, `system`, `template`, `license`, `renderer`, `parser` und
`adapters`. Unbekannte Anweisungen (z. B. `MESSAGE`) werden **nicht**
stillschweigend verworfen, sondern als Fehler gemeldet.

## Grenzen

* `FROM` muss ein Modell (oder eine Datei) sein, das auf dem Zielserver liegt.
  Ein neues Modell mit denselben Gewichten entsteht über `FROM <vorhandenes
  Modell>`; heruntergeladen wird nichts. Beim Ausrollen wird deshalb nur das
  Rezept übertragen, nie ein Blob.
* Kein Anlegen per Upload einer lokalen GGUF-Datei.
* Keine Anmeldung, keine Benutzerverwaltung. Schreibende Wege verlangen den
  Kopf `X-Anfrage: ollamaskope` (Schutz gegen fremde Formularseiten), das ist
  kein Ersatz für eine Anmeldung.
* `renderer`/`parser` werden mitgesendet; ob eine Ollama-Version sie beim
  Erzeugen beachtet, ist nicht geprüft.

## Tests

Die Schreibwege werden gegen `tests/fake-ollama.py` geprüft – ein
Ollama-Ersatz, der wie 0.40.14 das rohe `modelfile`-Feld ablehnt:

```bash
cd ~/ollamaskope
python3 -m unittest discover -s tests -v
```

Zurzeit sind es 40 Tests.

## Lizenz

Copyright (C) 2026 Olav Surawski (o-valo).

AGPL-3.0-or-later — siehe LICENSE.
Powered by AI

Dieses Projekt wurde mit Unterstützung KI-gestützter Werkzeuge für die Codeänderungen und die Dokumentation entwickelt. Der Code, die Tests und die Architekturentscheidungen stammen von einer menschlich verantwortlichen Person; für verbleibende Fehler ist entsprechend das Projekt verantwortlich.

Die eingesetzten Modelle werden nicht namentlich genannt. Die verwendeten Werkzeuge haben keinen Einfluss auf die Lizenz: Das Projekt steht weiterhin unter AGPL-3.0-or-later (siehe Lizenz).
