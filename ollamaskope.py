#!/usr/bin/env python3
"""ollamaskope.py - Web-Werkzeug für die Modelliste eines Ollama-Endpunkts.

Drei Dinge, mehr nicht:

    anzeigen    /api/tags + /api/ps (welche Modelle liegen da, welche sind geladen)
    Modelfile   /api/show, portabel gemacht (Blob-Pfade werden zu Modellnamen)
    erzeugen    /api/create   (aus dem bearbeiteten Modelfile, neuer Name)
    ausrollen   /api/show am Quell-Endpunkt, /api/create am Ziel (Rezept, keine Blobs)
    löschen     /api/delete   (nur mit exakt eingegebenem Modellnamen)
    Abhängigkeiten  /api/show je Modell, `details.parent_model` als Kette
    Endpunkte   /api/endpunkte eintragen/entfernen (schreibt config.json)
                Endpunkte aus ollamaskope.conf bleiben in dieser Datei

Das Werkzeug rechnet nicht. Es spricht die Ollama-API über HTTP und läuft
deshalb bewusst nicht auf einem Inferenz-Host (§5b der Wissensdatei).

Start:

    ./ollamaskope.sh start | stop | restart | status
    python3 ollamaskope.py --port 8090

Konfiguration: config.json - Endpunkte, Bind-Adresse, Port, Zeitlimit und
`schreiben` je Endpunkt. Daneben optional die zeilenweise `ollamaskope.conf`
(`schlüssel = wert`, ein Endpunkt je Zeile); sie hat Vorrang vor config.json.
Keine Anmeldung: der Dienst bindet standardmäßig nur
auf 127.0.0.1. Wer `bind` auf 0.0.0.0 setzt, entscheidet damit, wer Modelle
löschen darf.

Wichtig fürs Erzeugen: Ollama 0.40.14 nimmt das frühere Feld `modelfile`
nicht mehr an (Probe 16.11.2026: „neither 'from' or 'files' was specified“).
Deshalb zerlegt dieses Programm das Modelfile selbst und sendet `from`,
`parameters`, `system`, `template`, `license`, `renderer`, `parser`, `adapters`.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Iterator
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

VERSION = "1.0.1"
SCRIPT_DIR = Path(__file__).resolve().parent
STATIC_DIR = SCRIPT_DIR / "static"

# Eine Zeile je Lade-/Entladeversuch, getrennt von den Zugriffszeilen. Nur
# diese Datei sagt, was auf dem Zielhost passiert ist: Endpunkt, Modell, Dauer
# und `done_reason`. Auch Fehlschläge landen hier – genau sie beantworten
# später die Frage, warum ein 200 kam und trotzdem nichts im Speicher lag.
LADEN_LOG = SCRIPT_DIR / "laden.log"
_laden_log_sperre = threading.Lock()

MAX_KOERPER = 512 * 1024
MAX_MODELLFILE = 256 * 1024
MODELL_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
ERZEUGEN_TIMEOUT = 900.0
LADEN_TIMEOUT = 300.0
GRAPH_TTL = 120.0

STATISCHE_DATEIEN = {
    "index.html": "text/html; charset=utf-8",
    "app.js": "text/javascript; charset=utf-8",
    "style.css": "text/css; charset=utf-8",
    # Paket für den Ein-Zeilen-Installer, gebaut von paket-bauen.sh.
    "ollamaskope.tar.gz": "application/gzip",
}

DEFAULT_CONFIG: dict[str, Any] = {
    "bind": "127.0.0.1",
    "port": 8090,
    "timeout": 25,
    # Seltenes Feature, absichtlich aus: Ausrollen aus einer GGUF-Datei.
    "gguf": False,
    "endpunkte": [
        {
            "id": "lokal",
            "name": "lokal (127.0.0.1:11434)",
            "url": "http://127.0.0.1:11434",
            "schreiben": True,
        },
        {
            "id": "ollama-1",
            "name": "ollama-1 (10.0.0.24)",
            "url": "http://10.0.0.24:11434",
            "schreiben": True,
        },
        {
            "id": "ollama-2",
            "name": "ollama-2 (10.0.0.81)",
            "url": "http://10.0.0.81:11434",
            "schreiben": False,
        },
        {
            "id": "ollama-3",
            "name": "ollama-3 (10.0.0.79)",
            "url": "http://10.0.0.79:11434",
            "schreiben": False,
        },
    ],
}


class ConfigError(Exception):
    """config.json ist nicht brauchbar."""


class OllamaFehler(Exception):
    """Der Ollama-Endpunkt hat nicht wie erwartet geantwortet."""

    def __init__(self, text: str, status: int | None = None) -> None:
        super().__init__(text)
        self.status = status


def laden_protokollieren(
    ep: dict[str, Any], modell: str, behalten: bool, sekunden: float, ergebnis: str
) -> None:
    """Eine Zeile je Lade-/Entladeversuch, für die Fehlersuche.

    Felder mit Tabulator getrennt: Zeit, laden/entladen, Endpunktname,
    Endpunkt-URL, Modell, Dauer, Ergebnis (`ok done_reason=load` bzw.
    `fehler: …`). Das Protokoll ist Beiwerk – ein Schreibfehler darf den
    Vorgang nicht kippen.
    """
    zeile = "\t".join(
        (
            time.strftime("%Y-%m-%dT%H:%M:%S"),
            "laden" if behalten else "entladen",
            str(ep.get("name") or ep.get("id") or "?"),
            str(ep.get("url") or "?"),
            modell,
            f"{sekunden:.2f}s",
            " ".join(str(ergebnis).split()),
        )
    )
    try:
        with _laden_log_sperre:
            with open(LADEN_LOG, "a", encoding="utf-8") as datei:
                datei.write(zeile + "\n")
    except OSError as exc:
        print(f"laden.log nicht schreibbar: {exc}", file=sys.stderr)


class AnfrageFehler(Exception):
    """Die Anfrage selbst ist falsch (unbekannter Endpunkt, Name, ...)."""


class ModelfileFehler(Exception):
    """Das Modelfile lässt sich nicht senden."""


# --------------------------------------------------------------------------
# Konfiguration
# --------------------------------------------------------------------------

# Die alten Namen gelten weiter: wer das Werkzeug vor dem 17.11.2026
# eingerichtet hat, hat seine Endpunkte in ollama-sort.conf stehen. Die soll
# eine Umbenennung nicht verschwinden lassen.
EINFACHE_NAMEN = ("ollamaskope.conf", "ollamaskope.env")
ALTE_EINFACHE_NAMEN = ("ollama-sort.conf", "ollama-sort.env")

# Erlaubte Schlüssel der zeilenweisen Datei; deutsche und englische Schreibweise.
EINFACH_SCHLUESSEL = {
    "bind": "bind",
    "adresse": "bind",
    "host": "bind",
    "port": "port",
    "timeout": "timeout",
    "zeitlimit": "timeout",
    "endpunkt": "endpunkt",
    "endpunkte": "endpunkt",
    "endpoint": "endpunkt",
    "endpoints": "endpunkt",
    "gguf": "gguf",
    "gguf_ausrollen": "gguf",
    "datei_ausrollen": "gguf",
}
SCHREIBEN_JA = {"schreiben", "true", "ja", "j", "1", "rw", "yes", "an"}
SCHREIBEN_NEIN = {"lesen", "nur lesen", "false", "nein", "n", "0", "ro", "no", "aus"}


def einfache_config_pfad(
    json_pfad: Path | None = None, vorgabe: str | None = None
) -> Path:
    """Datei der zeilenweisen Konfiguration bestimmen (nicht öffnen).

    Reihenfolge: `--einfach`, `$OLLAMASKOPE_EINFACH` (auch `$OLLAMA_SORT_EINFACH`),
    dann `ollamaskope.conf` bzw. `ollamaskope.env` neben config.json – und die
    alten Namen `ollama-sort.conf`/`.env` weiter. Existiert keine, ist der
    Rückgabewert der erste Kandidat; ob er da ist, prüft der Aufrufer.
    """
    if vorgabe:
        return Path(vorgabe).expanduser()
    aus_umgebung = os.environ.get("OLLAMASKOPE_EINFACH") or os.environ.get(
        "OLLAMA_SORT_EINFACH"
    )
    if aus_umgebung:
        return Path(aus_umgebung).expanduser()
    basis = json_pfad.parent if json_pfad is not None else SCRIPT_DIR
    for name in EINFACHE_NAMEN + ALTE_EINFACHE_NAMEN:
        kandidat = basis / name
        if kandidat.is_file():
            return kandidat
    return basis / EINFACHE_NAMEN[0]


def _ohne_anfuehrungszeichen(wert: str) -> str:
    if len(wert) >= 2 and wert[0] == wert[-1] and wert[0] in "\"'":
        return wert[1:-1].strip()
    return wert


def _endpunkt_aus_zeile(
    datei: str, nummer: int, wert: str, gesehen: set[str]
) -> dict[str, Any]:
    """Eine Zeile `name | http://host:port | schreiben` zerlegen."""
    teile = [teil.strip() for teil in re.split(r"[|;]", wert) if teil.strip()]
    if not teile:
        raise ConfigError(f"{datei}:{nummer}: Endpunkt ist leer")
    url_index = next(
        (
            i
            for i, teil in enumerate(teile)
            if teil.lower().startswith(("http://", "https://"))
        ),
        None,
    )
    if url_index is None:
        raise ConfigError(
            f"{datei}:{nummer}: Endpunkt ohne http(s)-URL – Aufbau: "
            "endpunkt = name | http://host:port | schreiben"
        )
    url = teile[url_index].rstrip("/")
    if not re.match(r"^https?://[^\s/]+$", url):
        raise ConfigError(
            f"{datei}:{nummer}: {url} ist keine Adresse wie http://host:port"
        )
    if url in gesehen:
        raise ConfigError(f"{datei}:{nummer}: {url} steht schon weiter oben")
    gesehen.add(url)

    schreiben: bool | None = None
    name = ""
    for i, teil in enumerate(teile):
        if i == url_index:
            continue
        klein = teil.lower()
        if schreiben is None and klein in SCHREIBEN_JA:
            schreiben = True
        elif schreiben is None and klein in SCHREIBEN_NEIN:
            schreiben = False
        elif not name:
            name = teil
        else:
            raise ConfigError(
                f"{datei}:{nummer}: zu viele Angaben – erwartet "
                "name | http://host:port | schreiben"
            )
    if not name:
        name = urlparse(url).netloc or url
    kennung = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "endpunkt"
    return {
        "id": kennung[:40],
        "name": name,
        "url": url,
        "schreiben": bool(schreiben),
        "quelle": "conf",
    }


def lade_einfache_config(pfad: Path) -> dict[str, Any]:
    """Zeilenweise Konfiguration lesen: `schlüssel = wert`, `#` ist Kommentar."""
    try:
        text = pfad.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise ConfigError(f"{pfad} nicht lesbar: {exc}") from exc

    daten: dict[str, Any] = {"endpunkte": []}
    urls: set[str] = set()
    for nummer, rohzeile in enumerate(text.splitlines(), start=1):
        zeile = rohzeile.strip()
        if not zeile or zeile.startswith(("#", ";")):
            continue
        treffer = re.match(r"^([A-Za-z][\w.-]*)\s*[:=]\s*(.+)$", zeile)
        if not treffer:
            raise ConfigError(
                f"{pfad.name}:{nummer}: erwartet „schlüssel = wert“ – "
                f"gelesen: {zeile!r}"
            )
        schluessel = treffer.group(1).lower()
        for praefix in ("ollamaskope_", "ollama_sort_"):
            if schluessel.startswith(praefix):
                schluessel = schluessel[len(praefix) :]
                break
        ziel = EINFACH_SCHLUESSEL.get(schluessel)
        if ziel is None:
            raise ConfigError(
                f"{pfad.name}:{nummer}: unbekannter Schlüssel „{treffer.group(1)}“ "
                "– erlaubt: bind, port, timeout, endpunkt, gguf"
            )
        wert = _ohne_anfuehrungszeichen(treffer.group(2).strip())
        if not wert:
            raise ConfigError(f"{pfad.name}:{nummer}: Wert fehlt")
        if ziel == "endpunkt":
            daten["endpunkte"].append(
                _endpunkt_aus_zeile(pfad.name, nummer, wert, urls)
            )
        elif ziel == "port":
            try:
                daten["port"] = int(wert)
            except ValueError as exc:
                raise ConfigError(
                    f"{pfad.name}:{nummer}: Port muss eine Zahl sein"
                ) from exc
            if not 0 <= daten["port"] <= 65535:
                raise ConfigError(
                    f"{pfad.name}:{nummer}: Port muss zwischen 0 und 65535 liegen"
                )
        elif ziel == "timeout":
            try:
                daten["timeout"] = float(wert.replace(",", "."))
            except ValueError as exc:
                raise ConfigError(
                    f"{pfad.name}:{nummer}: Zeitlimit muss eine Zahl sein"
                ) from exc
        elif ziel == "gguf":
            klein = wert.lower()
            if klein in SCHREIBEN_JA:
                daten["gguf"] = True
            elif klein in SCHREIBEN_NEIN:
                daten["gguf"] = False
            else:
                raise ConfigError(
                    f"{pfad.name}:{nummer}: gguf muss ja oder nein sein"
                )
        else:
            daten["bind"] = wert
    return daten


def load_config(
    path: str | None = None, einfach: str | None = None
) -> tuple[dict[str, Any], Path, Path | None]:
    """config.json und die zeilenweise Konfiguration lesen und prüfen.

    Die zeilenweise Datei hat Vorrang: ihre Werte überschreiben bind, port und
    timeout, ihre Endpunkte stehen vorn. Endpunkte aus config.json kommen
    hinzu, soweit ihre URL nicht schon dort steht.
    """
    pfad = Path(
        path
        or os.environ.get("OLLAMASKOPE_CONFIG")
        or os.environ.get("OLLAMA_SORT_CONFIG")
        or (SCRIPT_DIR / "config.json")
    ).expanduser()
    einfach_pfad = einfache_config_pfad(pfad, einfach)
    einfach_daten = (
        lade_einfache_config(einfach_pfad) if einfach_pfad.is_file() else None
    )

    if pfad.is_file():
        try:
            roh = json.loads(pfad.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ConfigError(f"{pfad} nicht lesbar: {exc}") from exc
        if not isinstance(roh, dict):
            raise ConfigError(f"{pfad}: oben muss ein JSON-Objekt stehen")
        config = {**DEFAULT_CONFIG, **roh}
    else:
        config = dict(DEFAULT_CONFIG)
        config["endpunkte"] = [dict(ep) for ep in DEFAULT_CONFIG["endpunkte"]]
        pfad = Path("(Vorgabe, keine config.json)")

    if einfach_daten is not None:
        for schluessel in ("bind", "port", "timeout", "gguf"):
            if schluessel in einfach_daten:
                config[schluessel] = einfach_daten[schluessel]

    json_endpunkte = config.get("endpunkte")
    if json_endpunkte is None:
        json_endpunkte = []
    if not isinstance(json_endpunkte, list):
        raise ConfigError("endpunkte muss eine Liste sein")

    conf_endpunkte = list((einfach_daten or {}).get("endpunkte") or [])
    bekannt = {ep["url"] for ep in conf_endpunkte}
    uebrig = [
        ep
        for ep in json_endpunkte
        if not (
            isinstance(ep, dict) and str(ep.get("url") or "").rstrip("/") in bekannt
        )
    ]
    rohe_endpunkte = conf_endpunkte + uebrig
    if not rohe_endpunkte:
        raise ConfigError("endpunkte fehlt oder ist leer")

    gesehen: set[str] = set()
    endpunkte: list[dict[str, Any]] = []
    for nummer, roh_ep in enumerate(rohe_endpunkte, start=1):
        if not isinstance(roh_ep, dict):
            raise ConfigError(f"Endpunkt {nummer}: Objekt erwartet")
        url = str(roh_ep.get("url") or "").rstrip("/")
        if not url.startswith(("http://", "https://")):
            raise ConfigError(
                f"Endpunkt {nummer}: url muss mit http:// oder https:// beginnen"
            )
        kennung = str(roh_ep.get("id") or roh_ep.get("name") or f"endpunkt-{nummer}")
        kennung = re.sub(r"[^a-z0-9-]+", "-", kennung.lower()).strip("-")
        kennung = kennung or f"endpunkt-{nummer}"
        if kennung in gesehen:
            raise ConfigError(f"Endpunkt {nummer}: Kennung {kennung!r} doppelt")
        gesehen.add(kennung)
        endpunkte.append(
            {
                "id": kennung,
                "name": str(roh_ep.get("name") or kennung),
                "url": url,
                "schreiben": bool(roh_ep.get("schreiben", False)),
                "quelle": str(roh_ep.get("quelle") or "config"),
            }
        )

    config["endpunkte"] = endpunkte
    try:
        config["port"] = int(config.get("port", DEFAULT_CONFIG["port"]))
        config["timeout"] = float(config.get("timeout", DEFAULT_CONFIG["timeout"]))
    except (TypeError, ValueError) as exc:
        raise ConfigError("port/timeout müssen Zahlen sein") from exc
    config["bind"] = str(config.get("bind", DEFAULT_CONFIG["bind"]))
    # Ausrollen aus einer GGUF-Datei ist ein Feature für Sonderfälle, keine
    # Grundeinstellung: ohne ausdrückliches Ja bleibt es gesperrt.
    config["gguf"] = bool(config.get("gguf", False))
    return config, pfad, (einfach_pfad if einfach_daten is not None else None)


# --------------------------------------------------------------------------
# Ollama ansprechen
# --------------------------------------------------------------------------


def _fehlertext(exc: HTTPError) -> str:
    """Die Fehlermeldung aus einer Ollama-Antwort holen."""
    text = exc.read().decode("utf-8", "replace").strip()
    try:
        meldung = json.loads(text).get("error") or text
    except (json.JSONDecodeError, AttributeError):
        meldung = text
    return str(meldung).strip() or f"HTTP {exc.code}"


def ollama_anfrage(
    ep: dict[str, Any],
    pfad: str,
    payload: Any = None,
    methode: str | None = None,
    timeout: float | None = None,
) -> dict[str, Any]:
    """Eine JSON-Anfrage an den Endpunkt; Fehler werden zu OllamaFehler."""
    daten = None if payload is None else json.dumps(payload).encode("utf-8")
    if methode is None:
        methode = "POST" if daten is not None else "GET"
    anfrage = Request(
        ep["url"] + pfad,
        data=daten,
        method=methode,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(anfrage, timeout=timeout) as antwort:
            roh = antwort.read()
    except HTTPError as exc:
        raise OllamaFehler(_fehlertext(exc), exc.code) from exc
    except URLError as exc:
        raise OllamaFehler(f"{ep['name']} nicht erreichbar ({exc.reason})") from exc
    except TimeoutError as exc:
        raise OllamaFehler(
            f"{ep['name']}: Zeitüberschreitung nach {timeout or '?'} s"
        ) from exc

    if not roh.strip():
        return {}
    try:
        ergebnis = json.loads(roh.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise OllamaFehler(f"Antwort von {ep['name']} ist kein JSON") from exc
    return ergebnis if isinstance(ergebnis, dict) else {"ergebnis": ergebnis}


def ollama_strom(
    ep: dict[str, Any],
    pfad: str,
    payload: dict[str, Any],
    timeout: float = ERZEUGEN_TIMEOUT,
) -> Iterator[bytes]:
    """Einen langen Ollama-Aufruf lesen und die NDJSON-Zeilen einzeln weitergeben."""
    anfrage = Request(
        ep["url"] + pfad,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        antwort = urlopen(anfrage, timeout=timeout)
    except HTTPError as exc:
        raise OllamaFehler(_fehlertext(exc), exc.code) from exc
    except URLError as exc:
        raise OllamaFehler(f"{ep['name']} nicht erreichbar ({exc.reason})") from exc
    except TimeoutError as exc:
        raise OllamaFehler(f"{ep['name']}: Zeitüberschreitung") from exc

    with antwort:
        for zeile in antwort:
            if zeile.strip():
                yield zeile.strip()


def ollama_erzeugen_strom(
    ep: dict[str, Any], payload: dict[str, Any], timeout: float = ERZEUGEN_TIMEOUT
) -> Iterator[bytes]:
    """/api/create lesen und die NDJSON-Zeilen einzeln weitergeben."""
    return ollama_strom(ep, "/api/create", payload, timeout)


def gesundheit(endpunkte: list[dict[str, Any]], timeout: float = 3.0) -> dict[str, Any]:
    """Alle Endpunkte kurz und gleichzeitig anklopfen."""
    ergebnis: dict[str, dict[str, Any]] = {}

    def pruefen(ep: dict[str, Any]) -> None:
        try:
            daten = ollama_anfrage(ep, "/api/version", timeout=timeout)
            ergebnis[ep["id"]] = {"erreichbar": True, "version": daten.get("version")}
        except OllamaFehler as exc:
            ergebnis[ep["id"]] = {"erreichbar": False, "fehler": str(exc)}

    threads = [
        threading.Thread(target=pruefen, args=(ep,), daemon=True) for ep in endpunkte
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout + 1)

    liste = []
    for ep in endpunkte:
        stand = ergebnis.get(
            ep["id"], {"erreichbar": False, "fehler": "keine Antwort"}
        )
        liste.append({"id": ep["id"], "name": ep["name"], **stand})
    return {
        "ok": any(eintrag["erreichbar"] for eintrag in liste),
        "version": VERSION,
        "endpunkte": liste,
    }


# --------------------------------------------------------------------------
# Modelfile: zerlegen (senden) und bauen (anzeigen)
# --------------------------------------------------------------------------


def _direktiven(text: str) -> Iterator[tuple[str, str]]:
    """Zeilen zu Anweisungen machen; `\"\"\"`-Blöcke gehören zur Anweisung."""
    zeilen = text.splitlines()
    i = 0
    while i < len(zeilen):
        zeile = zeilen[i].strip()
        i += 1
        if not zeile or zeile.startswith("#"):
            continue
        teile = zeile.split(None, 1)
        befehl = teile[0].upper()
        rest = teile[1].strip() if len(teile) > 1 else ""
        if rest.startswith('"""'):
            inhalt = rest[3:]
            if inhalt.endswith('"""'):
                rest = inhalt[:-3]
            else:
                puffer = [inhalt] if inhalt else []
                while i < len(zeilen):
                    naechste = zeilen[i]
                    i += 1
                    if naechste.strip().endswith('"""'):
                        puffer.append(naechste.rstrip()[:-3])
                        break
                    puffer.append(naechste)
                rest = "\n".join(puffer).strip("\n")
        elif rest[:1] in ('"', "'") and not (
            len(rest) >= 2 and rest[-1] == rest[0]
        ):
            # Ollama schreibt mehrzeilige Werte als SYSTEM " … " – ein
            # Anführungszeichen je Seite. Ohne diesen Zweig würde die
            # Schlusszeile als eigene Anweisung gelesen und der Parser
            # meldete eine leere Anweisung (gesehen an qwen3.5-9b-babel-brief
            # auf ollama-1, 16.11.2026).
            zeichen = rest[0]
            anfang = rest[1:]
            puffer = [anfang] if anfang else []
            while i < len(zeilen):
                naechste = zeilen[i]
                i += 1
                if naechste.rstrip().endswith(zeichen):
                    puffer.append(naechste.rstrip()[:-1])
                    break
                puffer.append(naechste)
            rest = "\n".join(puffer).strip("\n")
        elif len(rest) >= 2 and rest[0] == rest[-1] and rest[0] in "\"'":
            rest = rest[1:-1]
        yield befehl, rest


def _wert(roh: str) -> Any:
    """Parameterwerte so tippen, wie /api/create sie erwartet."""
    klein = roh.lower()
    if klein in ("true", "false"):
        return klein == "true"
    if re.fullmatch(r"-?\d+", roh):
        return int(roh)
    if re.fullmatch(r"-?\d+\.\d+(?:[eE][-+]?\d+)?", roh):
        return float(roh)
    return roh


def modelfile_zerlegen(text: str) -> dict[str, Any]:
    """Modelfile in die Felder von /api/create übersetzen."""
    quellen: dict[str, Any] = {
        "from": None,
        "system": None,
        "template": None,
        "license": None,
        "renderer": None,
        "parser": None,
    }
    parameter: dict[str, Any] = {}
    adapter: list[str] = []
    unbekannt: list[str] = []
    weitere_from = 0

    for befehl, rest in _direktiven(text):
        if befehl == "FROM":
            if quellen["from"] is None:
                if not rest:
                    raise ModelfileFehler("FROM ohne Ziel.")
                quellen["from"] = rest.split()[0]
            else:
                weitere_from += 1
        elif befehl == "PARAMETER":
            name, _, wert = rest.partition(" ")
            name, wert = name.strip().lower(), wert.strip()
            if not name or not wert:
                raise ModelfileFehler("PARAMETER braucht Name und Wert.")
            if len(wert) >= 2 and wert[0] == wert[-1] and wert[0] in "\"'":
                wert = wert[1:-1]
            if name == "stop":
                parameter.setdefault("stop", [])
                if isinstance(parameter["stop"], list):
                    parameter["stop"].append(_wert(wert))
                else:
                    parameter["stop"] = [parameter["stop"], _wert(wert)]
            else:
                parameter[name] = _wert(wert)
        elif befehl in ("SYSTEM", "TEMPLATE", "LICENSE", "RENDERER", "PARSER"):
            quellen[befehl.lower()] = rest
        elif befehl == "ADAPTER":
            if rest:
                adapter.append(rest)
        else:
            unbekannt.append(befehl)

    if unbekannt:
        raise ModelfileFehler(
            "Diese Anweisung(en) kann das Werkzeug nicht senden: "
            + ", ".join(sorted(set(unbekannt)))
            + " – bitte entfernen oder mit „ollama create“ bauen."
        )

    return {
        **quellen,
        "parameters": parameter,
        "adapters": adapter,
        "warnungen": (
            ["Weitere FROM-Zeile(n) ignoriert – /api/create nimmt nur ein FROM."]
            if weitere_from
            else []
        ),
    }


def create_payload(name: str, teile: dict[str, Any]) -> dict[str, Any]:
    """Strukturierte /api/create-Anfrage aus den zerlegten Teilen bauen."""
    if not teile["from"]:
        raise ModelfileFehler("Das Modelfile enthält kein FROM.")
    payload: dict[str, Any] = {"model": name, "from": teile["from"], "stream": True}
    if teile["parameters"]:
        payload["parameters"] = teile["parameters"]
    for feld in ("system", "template", "license", "renderer", "parser"):
        if teile[feld]:
            payload[feld] = teile[feld]
    if teile["adapters"]:
        payload["adapters"] = teile["adapters"]
    return payload


def modelfile_bauen(
    show: dict[str, Any], modell: str, basis: str | None = None
) -> dict[str, Any]:
    """Aus /api/show ein Modelfile machen, das auf ein Modell zeigt, nicht auf Blobs.

    Ollama antwortet auf /api/show mit `FROM /usr/share/ollama/.ollama/models/
    blobs/sha256-...` (bei Modellen mit Projektor auch zweimal). Das ist auf dem
    Knoten gültig, aber nicht zum Nachbauen. Ollama selbst schreibt den Hinweis
    als Kommentar „# FROM <name>“ mit - der wird bevorzugt, danach
    details.parent_model, zuletzt der Modellname.
    """
    text = (show.get("modelfile") or "").strip()
    details = show.get("details") or {}
    warnungen: list[str] = []

    kommentar = None
    for zeile in text.splitlines():
        treffer = re.match(r"#\s*FROM\s+(\S+)\s*$", zeile.strip(), re.IGNORECASE)
        if treffer:
            kommentar = treffer.group(1)

    ersatz = basis or kommentar
    if not ersatz:
        eltern = str(details.get("parent_model") or "").strip()
        if eltern and not eltern.lower().endswith(".gguf"):
            ersatz = eltern
    if not ersatz:
        ersatz = modell

    zeilen: list[str] = []
    from_gesehen = False
    for zeile in text.splitlines():
        roh = zeile.strip()
        if not roh or roh.startswith("#"):
            continue
        if roh.upper().startswith("FROM "):
            ziel = roh[5:].strip()
            if "blobs/" in ziel or ziel.startswith("/"):
                if from_gesehen:
                    warnungen.append(
                        "Weitere FROM-Zeile (z. B. Projektor) entfernt – "
                        "ein neues Modell nimmt nur ein FROM."
                    )
                    continue
                zeilen.append(f"FROM {ersatz}")
                from_gesehen = True
                warnungen.append(
                    f"FROM zeigte auf einen Blob-Pfad; ersetzt durch „{ersatz}“ "
                    "(liegt auf dem Server)."
                )
                continue
            from_gesehen = True
        zeilen.append(zeile)

    if not zeilen:
        zeilen = [f"FROM {ersatz}"]
        for zeile in str(show.get("parameters") or "").splitlines():
            teile = re.split(r"\s+", zeile.strip(), maxsplit=1)
            if len(teile) == 2 and teile[0]:
                zeilen.append(f"PARAMETER {teile[0]} {teile[1]}")
        system = (show.get("system") or "").strip()
        if system:
            zeilen.append(f'SYSTEM """{system}"""')
        template = (show.get("template") or "").strip()
        if template:
            zeilen.append(f'TEMPLATE """{template}"""')
    elif not from_gesehen:
        zeilen.insert(0, f"FROM {ersatz}")

    return {
        "modelfile": "\n".join(zeilen).strip() + "\n",
        "warnungen": list(dict.fromkeys(warnungen)),
        "quelle": text,
    }


def ausroll_rezept(
    quelle: dict[str, Any],
    modell: str,
    timeout: float,
    gguf: bool = False,
    basis_datei: str = "",
) -> dict[str, Any]:
    """Was sich von einem Modell überhaupt übertragen lässt.

    Ollama gibt über HTTP keine Gewichte heraus. Es bleibt das Modelfile, und
    `details.parent_model` sagt, worauf es beruht – der Kommentar „# FROM …“
    im Modelfile taugt dafür **nicht**, Ollama schreibt dort immer den eigenen
    Namen hinein. Drei Arten (Probe 16.11.2026 an ollama-3 und ollama-1):

      pull     kein Elternteil: aus der Registry geladen. Ausrollen = auf dem Ziel
               dasselbe Modell ziehen; das gibt dieselben Gewichte.
      rezept   Elternteil ist ein anderes Modell: auf dem Ziel aus der Basis
               plus Parameter/Template/System neu bauen.
      datei    Elternteil ist eine GGUF-Datei: nur als Feature (`gguf`), und nur
               wenn dieselbe Datei auf dem Ziel liegt – kopiert wird nichts.
    """
    show = ollama_anfrage(quelle, "/api/show", {"model": modell}, timeout=timeout)
    details = show.get("details") or {}
    eltern = _eltern_aus_show(show)
    if not eltern:
        return {
            "art": "pull",
            "basis": "",
            "modelfile": "",
            "warnungen": [],
            "teile": None,
            "details": details,
        }
    if _ist_basisdatei(eltern):
        if not gguf:
            return {
                "art": "datei",
                "basis": eltern,
                "modelfile": "",
                "warnungen": [],
                "teile": None,
                "details": details,
            }
        # Freigeschaltet: aus der Datei bauen, die auf dem Ziel liegt.
        pfad = basis_datei or eltern
        gebaut = modelfile_bauen(show, modell, pfad)
        return {
            "art": "datei",
            "basis": pfad,
            "original": eltern,
            "modelfile": gebaut["modelfile"],
            "warnungen": gebaut["warnungen"],
            "teile": modelfile_zerlegen(gebaut["modelfile"]),
            "details": details,
        }
    gebaut = modelfile_bauen(show, modell, eltern)
    return {
        "art": "rezept",
        "basis": eltern,
        "modelfile": gebaut["modelfile"],
        "warnungen": gebaut["warnungen"],
        "teile": modelfile_zerlegen(gebaut["modelfile"]),
        "details": details,
    }


def ausroll_plan(
    rezept: dict[str, Any],
    name: str,
    ziel_modelle: list[str],
    basis_ziehen: bool = False,
) -> dict[str, Any]:
    """Was zu tun ist und was im Weg steht; `fehler` None heißt: los."""
    kurz_vorhanden = {_kurzname(eintrag) for eintrag in ziel_modelle}
    if _kurzname(name) in kurz_vorhanden:
        return {
            "fehler": (
                f"„{name}“ gibt es auf dem Ziel schon. Bitte einen anderen "
                "Namen eintragen – ein Ausrollen soll nichts überschreiben."
            )
        }
    art = rezept["art"]
    if art == "datei" and rezept.get("teile") is None:
        return {
            "fehler": (
                f"Dieses Modell ist aus einer Datei gebaut ({rezept['basis']}); "
                "die Gewichte liegen nur als Datei. Das Ausrollen aus einer "
                "GGUF ist ein Feature für Sonderfälle und nicht freigeschaltet: "
                "in config.json \"gguf\": true setzen oder in ollamaskope.conf "
                "\u201eggguf = ja\u201c. Dann muss dieselbe GGUF-Datei auf dem Ziel "
                "liegen – kopiert wird sie nicht."
            )
        }
    if art == "datei":
        pfad = str(rezept["basis"])
        if not (pfad.startswith("/") or pfad.lower().endswith(".gguf")):
            return {
                "fehler": (
                    f"\u201e{pfad}\u201c sieht nicht wie eine GGUF-Datei aus. "
                    "Erwartet wird ein Pfad wie /srv/gguf/modell.gguf."
                ),
            }
        return {"fehler": None, "ziehen": False}
    if art == "pull":
        return {"fehler": None, "ziehen": False}
    if _kurzname(str(rezept["basis"])) in kurz_vorhanden:
        return {"fehler": None, "ziehen": False}
    if basis_ziehen:
        return {"fehler": None, "ziehen": True}
    return {
        "fehler": (
            f"Die Basis „{rezept['basis']}“ liegt nicht auf dem Ziel. Häkchen "
            "„Basis bei Bedarf ziehen“ setzen, dann wird sie dort aus der "
            "Registry geladen – oder sie vorher hinlegen."
        )
    }


# --------------------------------------------------------------------------
# Abhängigkeiten: welches Modell baut auf welchem auf
# --------------------------------------------------------------------------

_graph_speicher: dict[str, tuple[float, dict[str, Any]]] = {}
_graph_sperre = threading.Lock()


def _kurzname(name: str) -> str:
    """`:latest` weg, damit „klein“ und „klein:latest“ dasselbe treffen."""
    return name[:-7] if name.endswith(":latest") else name


def _ist_basisdatei(wert: str) -> bool:
    """Werte, die kein Modell auf dem Endpunkt benennen."""
    wert = wert.strip().lower()
    return (
        not wert
        or wert.endswith(".gguf")
        or wert.startswith("/")
        or "blobs/" in wert
    )


def _eltern_aus_show(show: dict[str, Any]) -> str:
    """Der Ursprung eines Modells, wie Ollama ihn selbst führt.

    Der Kommentar `# FROM <name>` im Modelfile ist **nicht** der Ursprung:
    Ollama schreibt dort immer den Modellnamen selbst hinein („so baust du
    eine Kopie“). Verlässlich ist nur `details.parent_model`; es enthält bei
    von Hand gebauten Modellen den Elternteil, bei importierten eine Datei
    oder nichts (Probe 16.11.2026 an 18 Modellen auf ollama-1).
    """
    return str((show.get("details") or {}).get("parent_model") or "").strip()


def _graph_holen(ep: dict[str, Any], timeout: float) -> dict[str, Any]:
    """Für jedes Modell des Endpunkts den Elternteil erfragen (parallel)."""
    tags = ollama_anfrage(ep, "/api/tags", timeout=timeout)
    liste = tags.get("models") or []
    eltern: dict[str, str] = {}
    fehler: dict[str, str] = {}

    def holen(name: str) -> None:
        try:
            show = ollama_anfrage(ep, "/api/show", {"model": name}, timeout=timeout)
        except OllamaFehler as exc:
            fehler[name] = str(exc)
            return
        eltern[name] = _eltern_aus_show(show)

    namen = [str(m.get("name") or m.get("model") or "") for m in liste]
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(holen, namen))
    return {"modelle": liste, "eltern": eltern, "fehler": fehler}


def graph_verwerfen(endpunkt_id: str) -> None:
    """Nach Erzeugen oder Löschen ist die Kette veraltet."""
    with _graph_sperre:
        _graph_speicher.pop(endpunkt_id, None)


def abhaengigkeiten(
    ep: dict[str, Any], modell: str, timeout: float
) -> dict[str, Any]:
    """Worauf das Modell aufbaut und welche Modelle auf ihm aufbauen."""
    with _graph_sperre:
        stand = _graph_speicher.get(ep["id"])
    aus_speicher = bool(stand and time.monotonic() - stand[0] < GRAPH_TTL)
    graph = stand[1] if aus_speicher and stand else None
    if graph is None:
        graph = _graph_holen(ep, timeout)
        with _graph_sperre:
            _graph_speicher[ep["id"]] = (time.monotonic(), graph)

    liste = {str(m.get("name") or m.get("model") or ""): m for m in graph["modelle"]}
    eltern: dict[str, str] = graph["eltern"]

    def eintrag(name: str) -> dict[str, Any]:
        roh = liste.get(name) or {}
        details = roh.get("details") or {}
        return {
            "modell": name,
            "vorhanden": name in liste,
            "familie": details.get("family"),
            "parameter": details.get("parameter_size"),
            "quantisierung": details.get("quantization_level"),
            "groesse": roh.get("size"),
            "geaendert": roh.get("modified_at"),
        }

    nach_kurzname = {_kurzname(name): name for name in liste}
    eigener = modell if modell in liste else nach_kurzname.get(_kurzname(modell), modell)
    basis_roh = eltern.get(eigener, "")

    if _ist_basisdatei(basis_roh):
        basis = "datei" if basis_roh else "registry"
        baut_auf: list[dict[str, Any]] = []
    else:
        bekannter = nach_kurzname.get(_kurzname(basis_roh), basis_roh)
        baut_auf = [eintrag(bekannter)]
        basis = "modell" if bekannter in liste else "extern"

    darauf_bauen = sorted(
        (
            eintrag(name)
            for name, elternname in eltern.items()
            if not _ist_basisdatei(elternname)
            and _kurzname(elternname) == _kurzname(eigener)
            and name != eigener
        ),
        key=lambda eintrag_: str(eintrag_["modell"]),
    )

    geschwister: list[dict[str, Any]] = []
    if basis in ("modell", "extern"):
        geschwister = sorted(
            (
                eintrag(name)
                for name, elternname in eltern.items()
                if not _ist_basisdatei(elternname)
                and _kurzname(elternname) == _kurzname(basis_roh)
                and name != eigener
            ),
            key=lambda eintrag_: str(eintrag_["modell"]),
        )

    return {
        "endpunkt": ep["id"],
        "modell": eigener,
        "basis": basis,
        "basis_roh": basis_roh,
        "baut_auf": baut_auf,
        "darauf_bauen": darauf_bauen,
        "geschwister": geschwister,
        "geprueft": len(liste),
        "fehler": [
            {"modell": name, "fehler": text}
            for name, text in sorted(graph["fehler"].items())
        ],
        "aus_speicher": aus_speicher,
    }


# --------------------------------------------------------------------------
# HTTP-Dienst
# --------------------------------------------------------------------------


def _kennung_bilden(name: str, vorhanden: dict[str, Any]) -> str:
    """Aus dem Namen eine eindeutige Kennung machen (a-z, 0-9, -)."""
    basis = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "endpunkt"
    kennung = basis[:40]
    nummer = 2
    while kennung in vorhanden:
        kennung = f"{basis[:36]}-{nummer}"
        nummer += 1
    return kennung


def make_handler(
    config: dict[str, Any],
    static_dir: Path = STATIC_DIR,
    quiet: bool = False,
    konfigpfad: Path | None = None,
) -> type[BaseHTTPRequestHandler]:
    """Request-Handler; alles außer den statischen Dateien ist API."""
    endpunkte = {ep["id"]: ep for ep in config["endpunkte"]}
    vorgabe_timeout = float(config["timeout"])
    endpunkt_sperre = threading.Lock()

    def endpunkte_speichern() -> None:
        """Endpunkte in config.json schreiben, alte Fassung als .bak.

        Endpunkte aus der zeilenweisen Konfiguration bleiben draußen – sie
        gehören in ollamaskope.conf, sonst stünden sie doppelt.
        """
        config["endpunkte"] = [
            {name: wert for name, wert in ep.items() if name != "quelle"}
            for ep in endpunkte.values()
            if ep.get("quelle") != "conf"
        ]
        if konfigpfad is None:
            return
        inhalt = json.dumps(config, ensure_ascii=False, indent=2) + "\n"
        temp = konfigpfad.with_name(konfigpfad.name + ".tmp")
        temp.write_text(inhalt, encoding="utf-8")
        if konfigpfad.exists():
            shutil.copy2(konfigpfad, konfigpfad.with_name(konfigpfad.name + ".bak"))
        os.replace(temp, konfigpfad)

    class Handler(BaseHTTPRequestHandler):
        server_version = f"ollamaskope/{VERSION}"
        sys_version = ""

        # -- Wege ---------------------------------------------------------

        def do_GET(self) -> None:  # noqa: N802 - Namen gibt http.server vor
            self._get()

        def do_POST(self) -> None:  # noqa: N802
            self._post()

        def _get(self) -> None:
            zerlegt = urlparse(self.path)
            route = zerlegt.path.rstrip("/") or "/"
            query = parse_qs(zerlegt.query)

            if route == "/":
                self._datei("index.html")
                return
            if route == "/get.sh":
                # Der Installer selbst, damit curl … | sh von hier aus geht.
                self._sende_datei(
                    SCRIPT_DIR / "get.sh",
                    "text/x-shellscript; charset=utf-8",
                    "get.sh fehlt neben ollamaskope.py",
                )
                return
            if route.lstrip("/") in STATISCHE_DATEIEN:
                self._datei(route.lstrip("/"))
                return
            if route == "/api/endpunkte":
                self._json(
                    HTTPStatus.OK,
                    {
                        "endpunkte": [
                            {
                                "id": ep["id"],
                                "name": ep["name"],
                                "url": ep["url"],
                                "schreiben": ep["schreiben"],
                                "quelle": ep.get("quelle", "config"),
                            }
                            for ep in endpunkte.values()
                        ]
                    },
                )
                return
            if route == "/api/gesundheit":
                self._json(
                    HTTPStatus.OK, gesundheit(list(endpunkte.values()))
                )
                return

            try:
                if route == "/api/abhaengigkeiten":
                    ep = self._endpunkt_aus_query(query)
                    modell = str((query.get("modell") or [""])[-1]).strip()
                    if not MODELL_NAME.match(modell):
                        raise AnfrageFehler("Ungültiger Modellname.")
                    self._json(
                        HTTPStatus.OK, abhaengigkeiten(ep, modell, vorgabe_timeout)
                    )
                    return
                if route == "/api/modelle":
                    ep = self._endpunkt_aus_query(query)
                    tags = ollama_anfrage(ep, "/api/tags", timeout=vorgabe_timeout)
                    version = ollama_anfrage(
                        ep, "/api/version", timeout=vorgabe_timeout
                    ).get("version")
                    try:
                        ps = ollama_anfrage(ep, "/api/ps", timeout=vorgabe_timeout)
                    except OllamaFehler:
                        ps = {}
                    self._json(
                        HTTPStatus.OK,
                        {
                            "endpunkt": ep["id"],
                            "version": version,
                            "modelle": tags.get("models", []),
                            "geladen": [
                                {
                                    "name": eintrag.get("name")
                                    or eintrag.get("model"),
                                    "expires_at": eintrag.get("expires_at"),
                                }
                                for eintrag in ps.get("models", [])
                            ],
                        },
                    )
                    return
            except AnfrageFehler as exc:
                self._json(HTTPStatus.BAD_REQUEST, {"fehler": str(exc)})
                return
            except OllamaFehler as exc:
                self._json(HTTPStatus.BAD_GATEWAY, {"fehler": str(exc)})
                return

            self._json(
                HTTPStatus.NOT_FOUND,
                {
                    "fehler": "unbekannter Pfad",
                    "pfade": [
                        "/api/endpunkte",
                        "/api/modelle",
                        "/api/abhaengigkeiten",
                        "/api/modelfile",
                        "/api/erzeugen",
                        "/api/ausrollen",
                        "/api/loeschen",
                        "/api/laden",
                        "/api/entladen",
                        "/api/gesundheit",
                    ],
                },
            )

        def _post(self) -> None:
            # Schreibende Wege nur aus der Oberfläche: dieses Kopf-Feld kann
            # eine fremde Seite per Formular nicht setzen (kein CORS-Preflight).
            if self.headers.get("X-Anfrage") != "ollamaskope":
                self._json(
                    HTTPStatus.FORBIDDEN,
                    {"fehler": "Kopf X-Anfrage fehlt – Aufruf nur über die Oberfläche"},
                )
                return

            daten = self._koerper()
            if daten is None:
                return

            route = urlparse(self.path).path.rstrip("/") or "/"
            try:
                if route == "/api/endpunkte":
                    self._endpunkt_hinzufuegen(daten)
                    return
                if route == "/api/endpunkte/entfernen":
                    self._endpunkt_entfernen(daten)
                    return
                if route == "/api/ausrollen":
                    self._ausrollen(daten)
                    return
                if route == "/api/laden":
                    self._laden(self._endpunkt_aus_id(str(daten.get("endpunkt") or "")), daten, True)
                    return
                if route == "/api/entladen":
                    self._laden(self._endpunkt_aus_id(str(daten.get("endpunkt") or "")), daten, False)
                    return
                if route not in ("/api/modelfile", "/api/erzeugen", "/api/loeschen"):
                    self._json(
                        HTTPStatus.NOT_FOUND,
                        {"fehler": f"unbekannter Pfad: {route}"},
                    )
                    return
                ep = self._endpunkt_aus_id(str(daten.get("endpunkt") or ""))
                if route == "/api/modelfile":
                    self._modelfile(ep, daten)
                elif route == "/api/erzeugen":
                    self._erzeugen(ep, daten)
                else:
                    self._loeschen(ep, daten)
            except (AnfrageFehler, ModelfileFehler) as exc:
                self._json(HTTPStatus.BAD_REQUEST, {"fehler": str(exc)})
            except OllamaFehler as exc:
                self._json(HTTPStatus.BAD_GATEWAY, {"fehler": str(exc)})

        # -- Die drei Aktionen --------------------------------------------

        def _modelfile(self, ep: dict[str, Any], daten: dict[str, Any]) -> None:
            modell = str(daten.get("modell") or "").strip()
            if not MODELL_NAME.match(modell):
                raise AnfrageFehler("Ungültiger Modellname.")
            show = ollama_anfrage(
                ep, "/api/show", {"model": modell}, timeout=vorgabe_timeout
            )
            gebaut = modelfile_bauen(show, modell)
            self._json(
                HTTPStatus.OK,
                {
                    "modell": modell,
                    "modelfile": gebaut["modelfile"],
                    "warnungen": gebaut["warnungen"],
                    "details": show.get("details") or {},
                    "parameter": show.get("parameters") or "",
                    "system": show.get("system") or "",
                    "template": show.get("template") or "",
                    "capabilities": show.get("capabilities") or [],
                },
            )

        def _erzeugen(self, ep: dict[str, Any], daten: dict[str, Any]) -> None:
            if not self._darf_schreiben(ep):
                return
            name = str(daten.get("name") or "").strip()
            if not MODELL_NAME.match(name):
                raise ModelfileFehler(
                    "Ungültiger Modellname: erlaubt sind Buchstaben, Ziffern "
                    "und . _ - / : ohne Leerzeichen, am Anfang Buchstabe oder Ziffer."
                )
            text = str(daten.get("modelfile") or "")
            if not text.strip():
                raise ModelfileFehler("Das Modelfile ist leer.")
            if len(text) > MAX_MODELLFILE:
                raise ModelfileFehler("Modelfile zu groß (Grenze 256 KiB).")

            teile = modelfile_zerlegen(text)
            payload = create_payload(name, teile)

            self.send_response(HTTPStatus.OK)
            self.send_header(
                "Content-Type", "application/x-ndjson; charset=utf-8"
            )
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "close")
            self.end_headers()
            self.close_connection = True

            try:
                for warnung in teile["warnungen"]:
                    self._strom_zeile({"status": "hinweis", "hinweis": warnung})
                for zeile in ollama_erzeugen_strom(ep, payload):
                    self.wfile.write(zeile + b"\n")
                    self.wfile.flush()
            except OllamaFehler as exc:
                self._strom_zeile({"error": str(exc)})
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                graph_verwerfen(ep["id"])

        def _ausrollen(self, daten: dict[str, Any]) -> None:
            """Ein Modell auf einem anderen Endpunkt aus seinem Rezept nachbauen.

            Übertragen werden Modelfile, Parameter, Template und Systemtext –
            nicht die Blobs. Liegt die Basis auf dem Ziel, ist das Ausrollen sofort
            fertig; fehlt sie, kann sie auf Wunsch vorher gezogen werden.
            """
            quelle = self._endpunkt_aus_id(str(daten.get("quelle") or ""))
            ziel = self._endpunkt_aus_id(str(daten.get("ziel") or ""))
            if quelle["id"] == ziel["id"]:
                raise AnfrageFehler(
                    "Quelle und Ziel sind derselbe Endpunkt – zum Kopieren dort "
                    "genügt /api/copy, hier ist nichts zu tun."
                )
            if not self._darf_schreiben(ziel):
                return
            modell = str(daten.get("modell") or "").strip()
            if not MODELL_NAME.match(modell):
                raise AnfrageFehler("Ungültiger Modellname.")
            name = str(daten.get("name") or "").strip() or modell
            if not MODELL_NAME.match(name):
                raise ModelfileFehler(
                    "Ungültiger Zielname: erlaubt sind Buchstaben, Ziffern und "
                    ". _ - / : ohne Leerzeichen."
                )
            basis_ziehen = bool(daten.get("basis_ziehen"))
            basis_datei = str(daten.get("basis_datei") or "").strip()
            gguf = bool(config.get("gguf"))

            rezept = ausroll_rezept(
                quelle, modell, vorgabe_timeout, gguf=gguf, basis_datei=basis_datei
            )
            tags = ollama_anfrage(ziel, "/api/tags", timeout=vorgabe_timeout)
            ziel_modelle = [
                str(eintrag.get("name") or eintrag.get("model") or "")
                for eintrag in tags.get("models") or []
            ]
            plan = ausroll_plan(rezept, name, ziel_modelle, basis_ziehen)
            if plan["fehler"]:
                raise ModelfileFehler(plan["fehler"])

            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "close")
            self.end_headers()
            self.close_connection = True

            try:
                if rezept["art"] == "pull":
                    self._strom_zeile({"status": f"ziehe {modell} auf {ziel['name']}"})
                    self._pull_mit_fortschritt(ziel, modell)
                    if name != modell:
                        self._strom_zeile({"status": f"benenne um: {modell} → {name}"})
                        ollama_anfrage(
                            ziel,
                            "/api/copy",
                            {"source": modell, "destination": name},
                            timeout=vorgabe_timeout,
                        )
                    self._strom_zeile({"status": "success"})
                else:
                    for warnung in rezept["warnungen"]:
                        self._strom_zeile({"hinweis": warnung})
                    if plan["ziehen"]:
                        self._strom_zeile(
                            {
                                "status": f"ziehe Basis {rezept['basis']} "
                                f"auf {ziel['name']}"
                            }
                        )
                        self._pull_mit_fortschritt(ziel, str(rezept["basis"]))
                    self._strom_zeile(
                        {
                            "status": f"erzeuge {name} auf {ziel['name']} "
                            f"(FROM {rezept['basis']})"
                        }
                    )
                    for zeile in ollama_erzeugen_strom(
                        ziel, create_payload(name, rezept["teile"])
                    ):
                        self.wfile.write(zeile + b"\n")
                        self.wfile.flush()
                graph_verwerfen(ziel["id"])
            except OllamaFehler as exc:
                self._strom_zeile({"error": str(exc)})
            except (BrokenPipeError, ConnectionResetError):
                pass

        def _pull_mit_fortschritt(self, ep: dict[str, Any], modell: str) -> None:
            """Einen Pull mitlesen und nur Statuswechsel bzw. 10-%-Schritte melden."""
            letzter = ""
            for zeile in ollama_strom(
                ep, "/api/pull", {"model": modell, "stream": True}
            ):
                try:
                    stand = json.loads(zeile.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    continue
                if stand.get("error"):
                    raise OllamaFehler(str(stand["error"]))
                text = str(stand.get("status") or "")
                gesamt = int(stand.get("total") or 0)
                fertig = int(stand.get("completed") or 0)
                prozent = None
                if gesamt:
                    prozent = int(fertig * 100 / gesamt) // 10 * 10
                schluessel = f"{text}|{prozent}"
                if schluessel == letzter:
                    continue
                letzter = schluessel
                self._strom_zeile(
                    {
                        "status": text
                        + (f" {prozent} %" if prozent is not None else "")
                    }
                )

        def _loeschen(self, ep: dict[str, Any], daten: dict[str, Any]) -> None:
            if not self._darf_schreiben(ep):
                return
            modell = str(daten.get("modell") or "").strip()
            if not MODELL_NAME.match(modell):
                raise AnfrageFehler("Ungültiger Modellname.")
            bestaetigung = str(daten.get("bestaetigung") or "").strip()
            if bestaetigung != modell:
                raise AnfrageFehler(
                    "Bestätigung fehlt: der Modellname muss exakt eingegeben werden."
                )

            ollama_anfrage(
                ep,
                "/api/delete",
                {"model": modell},
                methode="DELETE",
                timeout=vorgabe_timeout,
            )
            graph_verwerfen(ep["id"])
            self._json(HTTPStatus.OK, {"ok": True, "geloescht": modell})

        # -- Modell laden und entladen -----------------------------------

        def _laden(
            self, ep: dict[str, Any], daten: dict[str, Any], behalten: bool
        ) -> None:
            """Wie `ollama run` (laden) bzw. `keep_alive: 0` (entladen)."""
            modell = str(daten.get("modell") or "").strip()
            if not MODELL_NAME.match(modell):
                raise AnfrageFehler("Ungültiger Modellname.")
            beginn = time.monotonic()
            try:
                antwort = ollama_anfrage(
                    ep,
                    "/api/generate",
                    {"model": modell, "keep_alive": "30m" if behalten else 0},
                    timeout=LADEN_TIMEOUT,
                )
            except OllamaFehler as exc:
                laden_protokollieren(
                    ep, modell, behalten, time.monotonic() - beginn, f"fehler: {exc}"
                )
                raise
            grund = antwort.get("done_reason")
            laden_protokollieren(
                ep,
                modell,
                behalten,
                time.monotonic() - beginn,
                f"ok done_reason={grund}",
            )
            self._json(
                HTTPStatus.OK,
                {
                    "ok": True,
                    "modell": modell,
                    "geladen": behalten,
                    "grund": grund,
                },
            )

        # -- Endpunkte eintragen und entfernen --------------------------

        def _endpunkt_hinzufuegen(self, daten: dict[str, Any]) -> None:
            name = str(daten.get("name") or "").strip()
            url = str(daten.get("url") or "").strip().rstrip("/")
            schreiben = bool(daten.get("schreiben"))
            if not name:
                raise AnfrageFehler("Name fehlt.")
            if len(name) > 60:
                raise AnfrageFehler("Name zu lang (höchstens 60 Zeichen).")
            if not re.match(r"^https?://[^\s/]+$", url):
                raise AnfrageFehler(
                    "URL bitte als http://host:port angeben, ohne Pfad – "
                    "z. B. http://10.0.0.50:11434"
                )
            with endpunkt_sperre:
                for vorhanden in endpunkte.values():
                    if vorhanden["url"].rstrip("/") == url:
                        raise AnfrageFehler(
                            f"{url} ist schon als „{vorhanden['name']}“ eingetragen."
                        )

            probe = {"id": "probe", "name": name, "url": url}
            try:
                version = ollama_anfrage(
                    probe, "/api/version", timeout=vorgabe_timeout
                ).get("version")
            except OllamaFehler as exc:
                raise AnfrageFehler(
                    f"{url} antwortet nicht wie ein Ollama-Endpunkt: {exc}"
                ) from exc

            with endpunkt_sperre:
                kennung = _kennung_bilden(name, endpunkte)
                eintrag = {
                    "id": kennung,
                    "name": name,
                    "url": url,
                    "schreiben": schreiben,
                }
                endpunkte[kennung] = eintrag
                try:
                    endpunkte_speichern()
                except OSError as exc:
                    endpunkte.pop(kennung, None)
                    raise AnfrageFehler(
                        f"config.json nicht schreibbar: {exc}"
                    ) from exc

            self._json(
                HTTPStatus.OK,
                {"ok": True, "endpunkt": eintrag, "version": version},
            )

        def _endpunkt_entfernen(self, daten: dict[str, Any]) -> None:
            kennung = str(daten.get("id") or "").strip()
            with endpunkt_sperre:
                if kennung not in endpunkte:
                    raise AnfrageFehler(
                        f"Unbekannter Endpunkt: {kennung or '(keiner)'}"
                    )
                eintrag = endpunkte.pop(kennung)
                try:
                    endpunkte_speichern()
                except OSError as exc:
                    endpunkte[kennung] = eintrag
                    raise AnfrageFehler(
                        f"config.json nicht schreibbar: {exc}"
                    ) from exc
            graph_verwerfen(kennung)
            self._json(HTTPStatus.OK, {"ok": True, "entfernt": eintrag})

        # -- Hilfen -------------------------------------------------------

        def _endpunkt_aus_query(self, query: dict[str, list[str]]) -> dict[str, Any]:
            return self._endpunkt_aus_id((query.get("endpunkt") or [""])[-1])

        def _endpunkt_aus_id(self, kennung: str) -> dict[str, Any]:
            ep = endpunkte.get(kennung)
            if ep is None:
                raise AnfrageFehler(
                    f"Unbekannter Endpunkt: {kennung or '(keiner)'} – "
                    "Kennungen stehen in config.json."
                )
            return ep

        def _darf_schreiben(self, ep: dict[str, Any]) -> bool:
            if ep["schreiben"]:
                return True
            self._json(
                HTTPStatus.FORBIDDEN,
                {
                    "fehler": f"{ep['name']} ist schreibgeschützt – in config.json "
                    'beim Endpunkt "schreiben": true setzen.'
                },
            )
            return False

        def _koerper(self) -> dict[str, Any] | None:
            try:
                laenge = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                laenge = 0
            if laenge <= 0:
                self._json(
                    HTTPStatus.LENGTH_REQUIRED, {"fehler": "leerer Anfragekörper"}
                )
                return None
            if laenge > MAX_KOERPER:
                self._json(
                    HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                    {"fehler": "Anfrage zu groß"},
                )
                return None
            roh = self.rfile.read(laenge)
            try:
                daten = json.loads(roh.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                self._json(HTTPStatus.BAD_REQUEST, {"fehler": "kein gültiges JSON"})
                return None
            if not isinstance(daten, dict):
                self._json(
                    HTTPStatus.BAD_REQUEST, {"fehler": "JSON-Objekt erwartet"}
                )
                return None
            return daten

        def _strom_zeile(self, obj: dict[str, Any]) -> None:
            try:
                self.wfile.write(
                    json.dumps(obj, ensure_ascii=False).encode("utf-8") + b"\n"
                )
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass

        def _datei(self, name: str) -> None:
            typ = STATISCHE_DATEIEN.get(name)
            if typ is None:
                self._json(HTTPStatus.NOT_FOUND, {"fehler": "unbekannte Datei"})
                return
            self._sende_datei(
                static_dir / name, typ, f"{name} fehlt im Ordner static/"
            )

        def _sende_datei(self, pfad: Path, typ: str, fehlt: str) -> None:
            try:
                inhalt = pfad.read_bytes()
            except OSError:
                self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"fehler": fehlt})
                return
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", typ)
            self.send_header("Content-Length", str(len(inhalt)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            try:
                self.wfile.write(inhalt)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def _json(self, code: HTTPStatus, obj: Any) -> None:
            inhalt = (json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(inhalt)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            try:
                self.wfile.write(inhalt)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            if not quiet:
                super().log_message(format, *args)

    return Handler


def serve(
    config: dict[str, Any],
    konfigpfad: Path,
    einfachpfad: Path | None = None,
    quiet: bool = False,
) -> int:
    """Dienst starten und bis Ctrl-C laufen lassen."""
    handler = make_handler(config, quiet=quiet, konfigpfad=konfigpfad)
    try:
        httpd = ThreadingHTTPServer((config["bind"], config["port"]), handler)
    except OSError as exc:
        print(f"Start fehlgeschlagen: {exc}", file=sys.stderr)
        return 2

    port = httpd.server_address[1]
    host = config["bind"]
    if host in ("0.0.0.0", ""):
        host = "127.0.0.1"
    quelle = f"{konfigpfad} + {einfachpfad}" if einfachpfad else f"{konfigpfad}"
    print(
        f"ollamaskope {VERSION}: http://{host}:{port}/  "
        f"(Config: {quelle}, {len(config['endpunkte'])} Endpunkte)",
        file=sys.stderr,
        flush=True,
    )
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Modelliste eines Ollama-Endpunkts als Web-Anwendung: anzeigen, "
            "Modelfile erzeugen, Modell erzeugen und löschen."
        )
    )
    parser.add_argument(
        "--config",
        metavar="PFAD",
        help="config.json (Standard: $OLLAMASKOPE_CONFIG oder config.json "
        "neben dem Skript).",
    )
    parser.add_argument(
        "--einfach",
        metavar="PFAD",
        help="zeilenweise Konfiguration (Standard: $OLLAMASKOPE_EINFACH, sonst "
        "ollamaskope.conf bzw. ollamaskope.env neben config.json).",
    )
    parser.add_argument(
        "--pruefen",
        "--prüfen",
        dest="pruefen",
        action="store_true",
        help="Konfiguration lesen und auflisten, dann beenden (startet nichts).",
    )
    parser.add_argument(
        "--bind",
        metavar="ADRESSE",
        help="Adresse zum Lauschen – überschreibt bind aus der Config.",
    )
    parser.add_argument(
        "--port",
        type=int,
        metavar="PORT",
        help="Port – überschreibt port aus der Config (0 = freier Port).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        metavar="SEKUNDEN",
        help="Zeitlimit für Ollama-Anfragen – überschreibt timeout.",
    )
    parser.add_argument(
        "--quiet", action="store_true", help="Keine Zugriffszeilen auf stderr."
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {VERSION}"
    )
    args = parser.parse_args(argv)
    if args.port is not None and not 0 <= args.port <= 65535:
        parser.error("--port muss zwischen 0 und 65535 liegen")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        config, pfad, einfachpfad = load_config(args.config, args.einfach)
    except ConfigError as exc:
        print(f"Konfigurationsfehler: {exc}", file=sys.stderr)
        return 3

    if args.bind is not None:
        config["bind"] = args.bind
    if args.port is not None:
        config["port"] = args.port
    if args.timeout is not None:
        config["timeout"] = args.timeout

    if args.pruefen:
        print(f"Config: {pfad}")
        if einfachpfad is not None:
            print(f"Einfach: {einfachpfad}")
        print(
            f"Bind {config['bind']}:{config['port']} · "
            f"{len(config['endpunkte'])} Endpunkte"
        )
        for ep in config["endpunkte"]:
            rechte = "schreiben" if ep["schreiben"] else "nur lesen"
            zusatz = " [conf]" if ep.get("quelle") == "conf" else ""
            print(f"  {ep['id']:14} {ep['name']} – {ep['url']} ({rechte}){zusatz}")
        return 0

    return serve(config, pfad, einfachpfad, quiet=args.quiet)


if __name__ == "__main__":
    sys.exit(main())
