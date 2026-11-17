#!/usr/bin/env bash
# ollamaskope.sh - Schalter für den Webdienst ollamaskope.py.
#
# Adresse, Port und Endpunkte stehen in config.json:
#
#   {"bind": "127.0.0.1", "port": 8090, "endpunkte": [...]}
#
# Aufruf:
#   ./ollamaskope.sh start | stop | restart | status
#
# Kein root, kein systemd: der Dienst läuft im Hintergrund (setsid), die PID
# steht in ollamaskope.pid, die Ausgabe in ollamaskope.log. Nach dem Start wird
# /api/gesundheit abgefragt - "gestartet" heißt hier, dass der Dienst antwortet
# und jeder Endpunkt seinen Stand gemeldet hat.

set -u

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Die alten Umgebungsvariablen gelten weiter, damit vorhandene Startskripte
# nicht brechen.
CONFIG="${OLLAMASKOPE_CONFIG:-${OLLAMA_SORT_CONFIG:-$DIR/config.json}}"
PYTHON="${PYTHON:-python3}"
# Falls install.sh ein venv angelegt hat (nur bei echten Abhängigkeiten), hat
# es Vorrang. Ohne .venv bleibt es beim System-Python.
if [ -x "$DIR/.venv/bin/python" ] &&
    [ -z "${OLLAMASKOPE_OHNE_VENV:-${OLLAMA_SORT_OHNE_VENV:-}}" ]; then
    PYTHON="$DIR/.venv/bin/python"
fi
SCRIPT="$DIR/ollamaskope.py"
PIDFILE="$DIR/ollamaskope.pid"
LOGFILE="$DIR/ollamaskope.log"

usage() {
    echo "Aufruf: $0 start|stop|restart|status" >&2
    exit 2
}

config_value() {
    "$PYTHON" - "$CONFIG" "$1" "$2" <<'PY'
import json
import sys

pfad, schluessel, vorgabe = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    with open(pfad, encoding="utf-8") as datei:
        wert = json.load(datei).get(schluessel, vorgabe)
except (OSError, json.JSONDecodeError):
    wert = vorgabe
print(wert)
PY
}

BIND="$(config_value bind 127.0.0.1)"
PORT="$(config_value port 8090)"
case "$BIND" in
    0.0.0.0|"") HOST="127.0.0.1" ;;
    ::|"::0") HOST="[::1]" ;;
    *) HOST="$BIND" ;;
esac
URL="http://$HOST:$PORT"

# $URL ist die Adresse für die Prüfung (bei 0.0.0.0 über Loopback).
# $ANZEIGE nennt zusätzlich die LAN-Adresse, unter der die Seite erreichbar ist.
ANZEIGE="$URL"
if [ "$BIND" = "0.0.0.0" ] || [ -z "$BIND" ]; then
    LAN_IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
    [ -n "$LAN_IP" ] && ANZEIGE="$URL · im LAN: http://$LAN_IP:$PORT"
fi

running_pid() {
    [ -f "$PIDFILE" ] || return 1
    pid="$(cat "$PIDFILE" 2>/dev/null)"
    case "$pid" in
        ''|*[!0-9]*) return 1 ;;
    esac
    [ -d "/proc/$pid" ] || return 1
    tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null | grep -q "ollamaskope.py" || return 1
    echo "$pid"
}

endpunkte_zeigen() {
    "$PYTHON" - "$1" <<'PY'
import json
import sys

try:
    daten = json.loads(sys.argv[1])
except json.JSONDecodeError:
    print("  (Gesundheitsbericht nicht lesbar)")
    raise SystemExit(0)
for eintrag in daten.get("endpunkte", []):
    if eintrag.get("erreichbar"):
        stand = eintrag.get("version") or "erreichbar"
    else:
        stand = eintrag.get("fehler") or "nicht erreichbar"
    print(f"  {eintrag.get('name')}: {stand}")
PY
}

cmd_start() {
    if pid="$(running_pid)"; then
        echo "läuft bereits (PID $pid) - $ANZEIGE"
        return 0
    fi

    setsid nohup "$PYTHON" "$SCRIPT" --config "$CONFIG" >>"$LOGFILE" 2>&1 </dev/null &
    pid=$!
    echo "$pid" >"$PIDFILE"

    antwort=""
    for _ in $(seq 1 40); do
        if antwort="$(curl -fsS --max-time 2 "$URL/api/gesundheit" 2>/dev/null)"; then
            break
        fi
        sleep 0.25
    done

    if [ -n "$antwort" ]; then
        echo "gestartet (PID $pid) - $ANZEIGE"
        endpunkte_zeigen "$antwort"
        return 0
    fi

    echo "Start fehlgeschlagen: $URL/api/gesundheit antwortet nicht." >&2
    tail -n 5 "$LOGFILE" >&2 2>/dev/null
    rm -f "$PIDFILE"
    return 1
}

cmd_stop() {
    if ! pid="$(running_pid)"; then
        rm -f "$PIDFILE"
        echo "läuft nicht"
        return 0
    fi
    kill -TERM "$pid" 2>/dev/null || true
    for _ in $(seq 1 20); do
        [ -d "/proc/$pid" ] || break
        sleep 0.25
    done
    if [ -d "/proc/$pid" ]; then
        echo "reagiert nicht auf SIGTERM, beende hart (PID $pid)" >&2
        kill -KILL "$pid" 2>/dev/null || true
    fi
    rm -f "$PIDFILE"
    echo "gestoppt (PID $pid)"
}

cmd_status() {
    echo "Config: $CONFIG  ·  $BIND:$PORT"
    if pid="$(running_pid)"; then
        echo "läuft (PID $pid) - $ANZEIGE"
        antwort="$(curl -fsS --max-time 3 "$URL/api/gesundheit" 2>/dev/null)"
        if [ -n "$antwort" ]; then
            endpunkte_zeigen "$antwort"
            return 0
        fi
        echo "Warnung: Prozess läuft, /api/gesundheit antwortet aber nicht." >&2
        return 1
    fi
    echo "gestoppt"
    return 1
}

case "${1:-}" in
    start) cmd_start ;;
    stop) cmd_stop ;;
    restart) cmd_stop && cmd_start ;;
    status) cmd_status ;;
    *) usage ;;
esac
