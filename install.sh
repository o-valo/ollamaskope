#!/usr/bin/env bash
# install.sh - ollamaskope einrichten.
#
# Prüft die Voraussetzungen, setzt die Rechte, legt config.json aus der Vorlage
# an und richtet den Kurzbefehl `ollamaskope` ein. Vorhandenes bleibt stehen:
# eine eigene config.json wird nie überschrieben.
#
# Aufruf:
#   ./install.sh                 prüfen und einrichten
#   ./install.sh --check         nur prüfen, nichts ändern
#   ./install.sh --test          einrichten, danach die Tests laufen lassen
#   ./install.sh --start         einrichten, danach den Dienst starten
#   ./install.sh --ohne-befehl   keinen Kurzbefehl in ~/.local/bin anlegen
#
# Kein venv: das Werkzeug braucht nur die Python-Standardbibliothek (http.server,
# urllib, json, threading). Ein venv entsteht deshalb nicht - es sei denn, es
# taucht eine requirements.txt auf; dann legt dieses Skript .venv an, und
# ollamaskope.sh nimmt automatisch dessen Python.

set -uo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${PYTHON:-python3}"
BIN_DIR="${HOME}/.local/bin"
BEFEHL="$BIN_DIR/ollamaskope"
CONFIG="$DIR/config.json"
VORLAGE="$DIR/config.example.json"
MINDESTENS="3.8"

CHECK=0
MIT_TEST=0
MIT_START=0
BEFEHL_ANLEGEN=1

while [ $# -gt 0 ]; do
    case "$1" in
        --check) CHECK=1 ;;
        --test) MIT_TEST=1 ;;
        --start) MIT_START=1 ;;
        --ohne-befehl) BEFEHL_ANLEGEN=0 ;;
        -h|--help) sed -n '2,18p' "$0" | sed 's/^# \{0,1\}//' ; exit 0 ;;
        *) echo "Unbekannt: $1 (--help zeigt den Aufruf)" >&2 ; exit 2 ;;
    esac
    shift
done

if [ -t 1 ]; then
    GRUEN=$'\033[32m' ; GELB=$'\033[33m' ; ROT=$'\033[31m' ; AUS=$'\033[0m'
else
    GRUEN="" ; GELB="" ; ROT="" ; AUS=""
fi

ok()    { printf '  %sok%s       %s\n' "$GRUEN" "$AUS" "$1" ; }
fehlt() { printf '  %sfehlt%s   %s\n' "$ROT" "$AUS" "$1" ; }
warn()  { printf '  %shinweis%s %s\n' "$GELB" "$AUS" "$1" ; }
info()  { printf '           %s\n' "$1" ; }
tun()   { printf '  %sneu%s      %s\n' "$GRUEN" "$AUS" "$1" ; }

FEHLER=0
GEMACHT=""

merken() { GEMACHT="${GEMACHT}${GEMACHT:+· }$1" ; }

echo "ollamaskope - Installation"
[ "$CHECK" = 1 ] && echo "(nur prüfen, es wird nichts geändert)"
echo

# --- 1. Systemvoraussetzungen --------------------------------------------
echo "Systemvoraussetzungen:"

if ! command -v "$PYTHON" >/dev/null 2>&1; then
    fehlt "$PYTHON"
    info "Debian/Ubuntu:  sudo apt-get install -y python3"
    echo
    echo "Abbruch: ohne python3 startet der Dienst nicht."
    exit 1
fi

if "$PYTHON" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' 2>/dev/null; then
    ok "$PYTHON $("$PYTHON" -c 'import sys; print("%d.%d.%d" % sys.version_info[:3])') (mindestens $MINDESTENS)"
else
    fehlt "$PYTHON ist älter als $MINDESTENS: $("$PYTHON" -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
    FEHLER=1
fi

if command -v curl >/dev/null 2>&1; then
    ok "curl (fragt /api/gesundheit nach dem Start ab)"
else
    fehlt "curl"
    info "Debian/Ubuntu:  sudo apt-get install -y curl"
    FEHLER=1
fi

if command -v hostname >/dev/null 2>&1 && command -v awk >/dev/null 2>&1; then
    ok "hostname, awk (nur für die LAN-Adresse in der Ausgabe)"
else
    warn "hostname/awk fehlen - die Startmeldung zeigt dann keine LAN-Adresse"
fi
echo

# --- 2. Dateien und Rechte -----------------------------------------------
echo "Dateien:"
DATEIEN=(
    "ollamaskope.py"
    "ollamaskope.sh"
    "install.sh"
    "get.sh"
    "config.example.json"
    "config.example.conf"
    "static/index.html"
    "static/app.js"
    "static/style.css"
)
for datei in "${DATEIEN[@]}"; do
    if [ ! -f "$DIR/$datei" ]; then
        fehlt "$datei"
        FEHLER=1
    elif [ ! -r "$DIR/$datei" ]; then
        fehlt "$datei (nicht lesbar)"
        FEHLER=1
    else
        ok "$datei"
    fi
done

for datei in ollamaskope.py ollamaskope.sh get.sh paket-bauen.sh tests/fake-ollama.py; do
    [ -f "$DIR/$datei" ] || continue
    if [ -x "$DIR/$datei" ]; then
        ok "$datei ist ausführbar"
    elif [ "$CHECK" = 1 ]; then
        warn "$datei ist nicht ausführbar (chmod +x fehlt)"
    else
        chmod +x "$DIR/$datei" && tun "$datei ausführbar gemacht"
        merken "Rechte gesetzt"
    fi
done
echo

# --- 3. Konfiguration -----------------------------------------------------
echo "Konfiguration:"
if [ -f "$CONFIG" ]; then
    if bericht="$("$PYTHON" - "$CONFIG" <<'PY'
import json
import sys

try:
    with open(sys.argv[1], encoding="utf-8") as datei:
        daten = json.load(datei)
except (OSError, json.JSONDecodeError) as fehler:
    print(f"nicht lesbar: {fehler}")
    raise SystemExit(1)
if not isinstance(daten, dict):
    print("oben steht kein JSON-Objekt")
    raise SystemExit(1)
if not isinstance(daten.get("endpunkte"), list) or not daten["endpunkte"]:
    print("Schlüssel 'endpunkte' fehlt, ist leer oder keine Liste")
    raise SystemExit(1)
print(f"{len(daten['endpunkte'])} Endpunkte, "
      f"Bind {daten.get('bind', '127.0.0.1')}:{daten.get('port', 8090)}")
PY
    )"; then
        ok "config.json: $bericht"
    else
        fehlt "config.json: $bericht"
        info "$CONFIG bleibt unangetastet - bitte von Hand berichtigen."
        FEHLER=1
    fi
elif [ -f "$VORLAGE" ]; then
    if [ "$CHECK" = 1 ]; then
        warn "config.json fehlt (würde aus config.example.json angelegt)"
    else
        cp "$VORLAGE" "$CONFIG" && tun "config.json aus config.example.json angelegt"
        merken "config.json angelegt"
        info "Endpunkte und Port dort eintragen, dann ./ollamaskope.sh start"
    fi
else
    fehlt "config.json und config.example.json fehlen beide"
    FEHLER=1
fi
echo

# --- 3b. Zeilenweise Konfiguration (freiwillig) --------------------------
echo "Einfache Konfiguration:"
CONF_DATEI=""
if [ -f "$DIR/ollamaskope.conf" ]; then
    CONF_DATEI="$DIR/ollamaskope.conf"
elif [ -f "$DIR/ollamaskope.env" ]; then
    CONF_DATEI="$DIR/ollamaskope.env"
fi

if [ -z "$CONF_DATEI" ]; then
    info "keine ollamaskope.conf - config.json gilt allein"
    if [ -f "$DIR/config.example.conf" ]; then
        info "optional: cp config.example.conf ollamaskope.conf"
    fi
elif [ ! -f "$DIR/ollamaskope.py" ]; then
    warn "$(basename "$CONF_DATEI") liegt da, ollamaskope.py fehlt - nicht geprüft"
elif meldung="$("$PYTHON" "$DIR/ollamaskope.py" --config "$CONFIG" \
        --einfach "$CONF_DATEI" --pruefen 2>&1)"; then
    ok "$(basename "$CONF_DATEI"): $(printf '%s\n' "$meldung" | grep -m1 'Endpunkte' || echo gelesen)"
    printf '%s\n' "$meldung" | grep '\[conf\]' | sed 's/^/           /'
else
    fehlt "$(basename "$CONF_DATEI"): $(printf '%s\n' "$meldung" | head -n 3)"
    FEHLER=1
fi
echo

# --- 4. venv - nur wenn wirklich Abhängigkeiten da sind -------------------
echo "Python-Umgebung:"
if [ -f "$DIR/requirements.txt" ]; then
    if [ -x "$DIR/.venv/bin/python" ]; then
        ok ".venv vorhanden (requirements.txt ist da)"
    elif [ "$CHECK" = 1 ]; then
        warn "requirements.txt gefunden, .venv fehlt (würde angelegt)"
    else
        if "$PYTHON" -m venv "$DIR/.venv" 2>/dev/null; then
            "$DIR/.venv/bin/python" -m pip -q install -r "$DIR/requirements.txt" \
                && tun ".venv angelegt und requirements.txt installiert"
            merken "venv"
        else
            fehlt ".venv ließ sich nicht anlegen"
            info "Debian/Ubuntu:  sudo apt-get install -y python3-venv"
            FEHLER=1
        fi
    fi
else
    ok "kein venv nötig - nur Python-Standardbibliothek, keine requirements.txt"
fi
echo

# --- 5. Kurzbefehl --------------------------------------------------------
echo "Kurzbefehl:"
if [ "$BEFEHL_ANLEGEN" = 0 ]; then
    info "übersprungen (--ohne-befehl)"
elif [ -f "$BEFEHL" ] && grep -qF "exec \"$DIR/ollamaskope.sh\"" "$BEFEHL"; then
    ok "$BEFEHL zeigt auf dieses Verzeichnis"
elif [ -f "$BEFEHL" ]; then
    warn "$BEFEHL existiert bereits und zeigt woandershin - bleibt unangetastet"
elif [ "$CHECK" = 1 ]; then
    warn "$BEFEHL fehlt (würde angelegt)"
else
    mkdir -p "$BIN_DIR"
    cat >"$BEFEHL" <<EOF
#!/usr/bin/env bash
# Kurzbefehl für ollamaskope, angelegt von $DIR/install.sh.
exec "$DIR/ollamaskope.sh" "\$@"
EOF
    chmod +x "$BEFEHL" && tun "$BEFEHL angelegt"
    merken "Kurzbefehl ollamaskope"
fi

case ":$PATH:" in
    *":$BIN_DIR:"*) ok "$BIN_DIR liegt im PATH" ;;
    *) warn "$BIN_DIR fehlt im PATH - dann ./ollamaskope.sh benutzen" ;;
esac
echo

# --- 6. Abschluss ---------------------------------------------------------
if [ "$FEHLER" != 0 ]; then
    echo "Nicht fertig: siehe 'fehlt' oben."
    exit 1
fi

if [ "$CHECK" = 1 ]; then
    echo "Prüfung durchgelaufen."
    exit 0
fi

echo "Fertig${GEMACHT:+ ($GEMACHT)}."
echo "Start:   ./ollamaskope.sh start      (oder: ollamaskope start)"
echo "Status:  ./ollamaskope.sh status"

if [ "$MIT_TEST" = 1 ]; then
    echo
    echo "Tests:"
    if ! "$PYTHON" -m unittest discover -s "$DIR/tests" -v; then
        echo "Tests fehlgeschlagen." >&2
        exit 1
    fi
fi

if [ "$MIT_START" = 1 ]; then
    echo
    if ! "$DIR/ollamaskope.sh" start; then
        echo "Start fehlgeschlagen - siehe $DIR/ollamaskope.log" >&2
        exit 1
    fi
fi
