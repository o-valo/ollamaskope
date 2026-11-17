#!/usr/bin/env bash
# paket-bauen.sh - static/ollamaskope.tar.gz für den Ein-Zeilen-Installer bauen.
#
#   ./paket-bauen.sh
#   curl -fsSL http://<host>:8090/get.sh | sh
#
# Ins Paket kommen Programm, Oberfläche, Startskript, Installer, Vorlagen und
# Tests. Nicht hinein kommen: config.json (bleibt beim Update stehen),
# PID-/Logdateien, .venv, __pycache__ und das Paket selbst.

set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ELTERN="$(dirname "$DIR")"
NAME="$(basename "$DIR")"
PAKET="$DIR/static/ollamaskope.tar.gz"

cd "$DIR"
for datei in ollamaskope.py ollamaskope.sh install.sh get.sh; do
    [ -f "$datei" ] || { echo "Fehlt: $datei" >&2; exit 1; }
done

mkdir -p "$DIR/static"
tar -czf "$PAKET" -C "$ELTERN" \
    --exclude="$NAME/config.json" \
    --exclude="$NAME/config.json.bak" \
    --exclude="$NAME/config.json.tmp" \
    --exclude="$NAME/*.pid" \
    --exclude="$NAME/*.log" \
    --exclude="$NAME/.venv" \
    --exclude="$NAME/__pycache__" \
    --exclude="$NAME/tests/__pycache__" \
    --exclude="$NAME/static/ollamaskope.tar.gz" \
    "$NAME"

echo "Paket:  $PAKET"
echo "Größe:  $(du -h "$PAKET" | cut -f1)"
echo "Inhalt:"
tar -tzf "$PAKET" | sed 's/^/  /'
