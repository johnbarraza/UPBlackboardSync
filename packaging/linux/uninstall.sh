#!/usr/bin/env sh
set -eu

DATA_HOME=${XDG_DATA_HOME:-"$HOME/.local/share"}
BIN_HOME=${XDG_BIN_HOME:-"$HOME/.local/bin"}
CONFIG_HOME=${XDG_CONFIG_HOME:-"$HOME/.config"}
DESKTOP_ID=app.bbsync.BlackboardSync.desktop

rm -rf "$DATA_HOME/blackboardsync"
rm -f "$BIN_HOME/blackboardsync"
rm -f "$DATA_HOME/applications/$DESKTOP_ID"
rm -f "$DATA_HOME/icons/hicolor/scalable/apps/app.bbsync.BlackboardSync.svg"
rm -f "$CONFIG_HOME/autostart/$DESKTOP_ID"

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$DATA_HOME/applications" >/dev/null 2>&1 || true
fi

echo "BlackboardSync fue desinstalado."
echo "Tus ajustes y descargas se conservaron."
echo "Para borrar los ajustes manualmente: rm -rf '$CONFIG_HOME/BlackboardSync'"
