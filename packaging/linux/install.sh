#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
SOURCE_DIR="$SCRIPT_DIR/BlackboardSync"

DATA_HOME=${XDG_DATA_HOME:-"$HOME/.local/share"}
BIN_HOME=${XDG_BIN_HOME:-"$HOME/.local/bin"}
APP_DIR="$DATA_HOME/blackboardsync"
APPLICATIONS_DIR="$DATA_HOME/applications"
ICONS_DIR="$DATA_HOME/icons/hicolor/scalable/apps"
AUTOSTART_DIR=${XDG_CONFIG_HOME:-"$HOME/.config"}/autostart
DESKTOP_ID=app.bbsync.BlackboardSync.desktop
AUTOSTART=1

if [ "${1:-}" = "--no-autostart" ]; then
    AUTOSTART=0
elif [ "$#" -gt 0 ]; then
    echo "Uso: ./install.sh [--no-autostart]" >&2
    exit 2
fi

if [ ! -f "$SOURCE_DIR/BlackboardSync" ]; then
    echo "No se encontro el ejecutable en $SOURCE_DIR/BlackboardSync" >&2
    echo "Ejecuta install.sh desde el paquete Linux descomprimido." >&2
    exit 1
fi

mkdir -p "$DATA_HOME" "$BIN_HOME" "$APPLICATIONS_DIR" "$ICONS_DIR"
rm -rf "$APP_DIR"
cp -R "$SOURCE_DIR" "$APP_DIR"
chmod +x "$APP_DIR/BlackboardSync"
cp "$SCRIPT_DIR/uninstall.sh" "$APP_DIR/uninstall.sh"
chmod +x "$APP_DIR/uninstall.sh"
cp "$SCRIPT_DIR/blackboardsync-launcher" "$APP_DIR/blackboardsync-launcher"
chmod +x "$APP_DIR/blackboardsync-launcher"
ln -sfn "$APP_DIR/blackboardsync-launcher" "$BIN_HOME/blackboardsync"

sed "s|^Exec=.*|Exec=\"$APP_DIR/blackboardsync-launcher\"|" \
    "$SCRIPT_DIR/$DESKTOP_ID" > "$APPLICATIONS_DIR/$DESKTOP_ID"
cp "$SCRIPT_DIR/app.bbsync.BlackboardSync.svg" \
    "$ICONS_DIR/app.bbsync.BlackboardSync.svg"

if [ "$AUTOSTART" -eq 1 ]; then
    mkdir -p "$AUTOSTART_DIR"
    cp "$APPLICATIONS_DIR/$DESKTOP_ID" "$AUTOSTART_DIR/$DESKTOP_ID"
else
    rm -f "$AUTOSTART_DIR/$DESKTOP_ID"
fi

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$APPLICATIONS_DIR" >/dev/null 2>&1 || true
fi

echo "BlackboardSync instalado para el usuario actual."
echo "Ejecutable: $BIN_HOME/blackboardsync"
echo "Tambien puedes abrirlo desde el menu de aplicaciones."
if [ "$AUTOSTART" -eq 1 ]; then
    echo "Inicio automatico: habilitado."
else
    echo "Inicio automatico: deshabilitado."
fi
case ":$PATH:" in
    *":$BIN_HOME:"*) ;;
    *) echo "Nota: agrega $BIN_HOME a PATH para ejecutar 'blackboardsync' desde la terminal." ;;
esac
