#!/bin/sh
# get.sh - ollamaskope aus dem LAN holen und einrichten.
#
#   curl -fsSL http://127.0.0.1:8090/get.sh | sh
#   curl -fsSL http://127.0.0.1:8090/get.sh | sh -s -- --bind 0.0.0.0
#
# Ablauf: Paket (ollamaskope.tar.gz) holen, nach ~/ollamaskope entpacken,
# install.sh laufen lassen, auf Wunsch starten. Bei einem Update bleiben
# config.json und ollamaskope.conf stehen - das Paket enthält sie nicht.
#
# Weil beim Rohr die Standardeingabe das Skript selbst ist, kommen Rückfragen
# über /dev/tty. Ohne Terminal bleiben config.json und Startzustand unverändert.
#
# Exit 0 = eingerichtet, 1 = Fehler, 2 = falscher Aufruf.

set -eu

# Ollamaskope hieß bis 17.11.2026 ollama-sort: die alten Variablennamen gelten
# weiter, damit vorhandene Aufrufe nicht brechen.
QUELLE="${OLLAMASKOPE_QUELLE:-${OLLAMA_SORT_QUELLE:-http://127.0.0.1:8090/ollamaskope.tar.gz}}"
ZIEL="${OLLAMASKOPE_ZIEL:-${OLLAMA_SORT_ZIEL:-$HOME/ollamaskope}}"
BIND=""
START="frage"
FRAGE_ANTWORT=""

# Beim Rohr ist stdin das Skript selbst, Rückfragen brauchen ein echtes
# Terminal. /dev/tty existiert auch ohne steuerndes Terminal - deshalb wird
# das Öffnen probiert statt nur -r/-w gefragt (sonst: „cannot create /dev/tty“).
TTY=""
if ( : </dev/tty ) 2>/dev/null && ( : >/dev/tty ) 2>/dev/null; then
    TTY="/dev/tty"
fi

hilfe() {
    cat <<'TEXT'
get.sh - ollamaskope holen und einrichten

  curl -fsSL http://127.0.0.1:8090/get.sh | sh
  curl -fsSL http://127.0.0.1:8090/get.sh | sh -s -- --bind 0.0.0.0

  --bind ADRESSE   127.0.0.1 (nur dieser Rechner) oder 0.0.0.0 (ganzes LAN)
  --quelle URL     anderes Paket statt http://127.0.0.1:8090/...
  --ziel PFAD      anderes Zielverzeichnis statt ~/ollamaskope
  --start          Dienst am Ende starten
  --ohne-start     Dienst nicht starten und nicht fragen
  --hilfe          diese Übersicht

Ohne --bind und ohne Terminal bleibt der Wert aus config.json (bei einer
neuen Installation 127.0.0.1). Gestartet wird nur mit --start.
TEXT
}

frage() { # $1 = Frage, $2 = Vorgabe -> FRAGE_ANTWORT
    FRAGE_ANTWORT=""
    if [ -n "$TTY" ]; then
        printf '%s ' "$1" >"$TTY" || true
        IFS= read -r FRAGE_ANTWORT <"$TTY" || FRAGE_ANTWORT=""
    fi
    if [ -z "$FRAGE_ANTWORT" ]; then
        FRAGE_ANTWORT="$2"
    fi
}

hole() { # $1 = URL, $2 = Datei
    if command -v curl >/dev/null 2>&1; then
        curl -fsSL --max-time 180 "$1" -o "$2"
    elif command -v wget >/dev/null 2>&1; then
        wget -q -O "$2" "$1"
    else
        echo "Fehler: weder curl noch wget vorhanden." >&2
        exit 1
    fi
}

while [ $# -gt 0 ]; do
    case "$1" in
        --bind)
            [ $# -ge 2 ] || { echo "--bind braucht eine Adresse" >&2; exit 2; }
            BIND="$2"; shift 2 ;;
        --bind=*) BIND="${1#--bind=}"; shift ;;
        --quelle)
            [ $# -ge 2 ] || { echo "--quelle braucht eine URL" >&2; exit 2; }
            QUELLE="$2"; shift 2 ;;
        --quelle=*) QUELLE="${1#--quelle=}"; shift ;;
        --ziel)
            [ $# -ge 2 ] || { echo "--ziel braucht einen Pfad" >&2; exit 2; }
            ZIEL="$2"; shift 2 ;;
        --ziel=*) ZIEL="${1#--ziel=}"; shift ;;
        --start) START="ja"; shift ;;
        --ohne-start) START="nein"; shift ;;
        -h|--hilfe|--help) hilfe; exit 0 ;;
        *) echo "Unbekannt: $1 (--hilfe zeigt den Aufruf)" >&2; exit 2 ;;
    esac
done

case "$BIND" in
    ""|127.0.0.1|0.0.0.0) ;;
    *)
        echo "Fehler: --bind kennt nur 127.0.0.1 und 0.0.0.0 (nicht: $BIND)" >&2
        exit 2 ;;
esac

for werkzeug in tar mktemp; do
    command -v "$werkzeug" >/dev/null 2>&1 || {
        echo "Fehler: $werkzeug fehlt." >&2
        exit 1
    }
done

echo "ollamaskope - Installation"
echo "  Quelle: $QUELLE"
echo "  Ziel:   $ZIEL"
echo

if [ -z "$BIND" ] && [ -n "$TTY" ]; then
    {
        echo "Womit soll der Dienst lauschen?"
        echo "  1) 127.0.0.1  nur dieser Rechner (Vorgabe, ohne Anmeldung sicher)"
        echo "  2) 0.0.0.0    im ganzen LAN erreichbar - ohne Anmeldung!"
    } >"$TTY" || true
    frage "Auswahl [1]:" "1"
    case "$FRAGE_ANTWORT" in
        2|0.0.0.0|lan|LAN) BIND="0.0.0.0" ;;
        *) BIND="127.0.0.1" ;;
    esac
    printf '\n' >"$TTY" || true
fi

TMP="$(mktemp -d "${TMPDIR:-/tmp}/ollamaskope-holen.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT HUP INT TERM

echo "Lade Paket ..."
if ! hole "$QUELLE" "$TMP/paket.tar.gz"; then
    echo "Fehler: $QUELLE ließ sich nicht laden." >&2
    exit 1
fi
tar -xzf "$TMP/paket.tar.gz" -C "$TMP"
if [ ! -f "$TMP/ollamaskope/ollamaskope.py" ]; then
    echo "Fehler: im Paket fehlt ollamaskope/ollamaskope.py." >&2
    exit 1
fi

if [ -d "$ZIEL" ]; then
    echo "Aktualisiere $ZIEL (config.json und ollamaskope.conf bleiben stehen) ..."
    cp -a "$TMP/ollamaskope/." "$ZIEL/"
else
    echo "Entpacke nach $ZIEL ..."
    mkdir -p "$(dirname "$ZIEL")"
    mv "$TMP/ollamaskope" "$ZIEL"
fi

if ! command -v bash >/dev/null 2>&1; then
    echo "Fehler: bash fehlt - install.sh braucht bash." >&2
    exit 1
fi

echo
bash "$ZIEL/install.sh" || exit 1

if [ -n "$BIND" ]; then
    python3 - "$ZIEL/config.json" "$BIND" <<'PY'
import json
import os
import sys

pfad, neu = sys.argv[1], sys.argv[2]
try:
    with open(pfad, encoding="utf-8") as datei:
        daten = json.load(datei)
except (OSError, json.JSONDecodeError):
    print(f"  config.json nicht lesbar - bind bitte von Hand setzen: {neu}")
    raise SystemExit(0)
alt = daten.get("bind")
if alt == neu:
    print(f"  bind: {neu} (unverändert)")
    raise SystemExit(0)
daten["bind"] = neu
temp = pfad + ".tmp"
with open(temp, "w", encoding="utf-8") as datei:
    json.dump(daten, datei, ensure_ascii=False, indent=2)
    datei.write("\n")
os.replace(temp, pfad)
print(f"  bind: {alt} -> {neu} (config.json)")
PY
fi

if [ "$START" = "frage" ]; then
    if [ -n "$TTY" ]; then
        frage "Dienst jetzt starten? [J/n]" "j"
        case "$FRAGE_ANTWORT" in
            [nN]*) START="nein" ;;
            *) START="ja" ;;
        esac
    else
        START="nein"
    fi
fi

echo
if [ "$START" = "ja" ]; then
    bash "$ZIEL/ollamaskope.sh" start || exit 1
else
    echo "Start später:  bash $ZIEL/ollamaskope.sh start"
fi
