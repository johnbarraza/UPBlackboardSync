# BlackboardSync para Linux

Este paquete contiene la aplicacion y sus dependencias Python. No necesitas
instalar Python, PyQt ni ejecutar el instalador como root.

## Instalar

```sh
tar -xzf BlackboardSync-*-linux-x86_64.tar.gz
cd BlackboardSync-*-linux-x86_64
./install.sh
```

Para instalar sin inicio automatico:

```sh
./install.sh --no-autostart
```

Despues abre **Blackboard Sync** desde el menu de aplicaciones o ejecuta
`~/.local/bin/blackboardsync`.

## Dependencias del sistema

En un escritorio completo normalmente ya estan instaladas. Si la aplicacion no
abre o Qt informa que no puede cargar `xcb`, instala:

Ubuntu/Debian:

```sh
sudo apt install libxcb-cursor0 libxkbcommon-x11-0 libnss3 xdg-utils \
  libxcomposite1 libxdamage1 libxrandr2 libxtst6 libxkbfile1 \
  libxcb-keysyms1 libxcb-shape0 libxcb-icccm4
```

Arch Linux/Omarchy:

```sh
sudo pacman -S --needed xcb-util-cursor libxkbcommon-x11 nss alsa-lib xdg-utils \
  libxcomposite libxdamage libxrandr libxtst libxkbfile \
  xcb-util-keysyms xcb-util-wm
```

En Wayland/Hyprland Qt selecciona Wayland o XWayland automaticamente. Si el
icono de bandeja no aparece, revisa que la barra usada por tu sesion tenga
habilitado el modulo de system tray.

## Desinstalar

Ejecuta `~/.local/share/blackboardsync/uninstall.sh`. Tambien puedes usar
`./uninstall.sh` desde el paquete descomprimido. La configuracion en
`~/.config/BlackboardSync` y las descargas se conservan.
