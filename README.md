# UP BlackboardSync

Este repositorio es un fork del proyecto original BlackboardSync.
Repositorio original: https://github.com/sanjacob/BlackboardSync

Mantenimiento local para uso en Universidad del Pacifico (Peru).
Licencia: GPL-2.0 (se mantiene la licencia del proyecto original).

## Distribucion

Este proyecto publica dos tipos de archivos:

- Aplicacion de escritorio (desktop) usa el API de blackboard (más preciso).
- Extension de navegador para Chrome y Firefox (scrape la pagina, es más proclive a errores).

## Linux (Ubuntu y Arch/Omarchy)

Las versiones Linux se distribuyen como
`BlackboardSync-VERSION-linux-x86_64.tar.gz`. El paquete incluye Python y las
dependencias de la aplicacion, por lo que no es necesario instalar PyQt ni usar
`pip` en el sistema.

```sh
tar -xzf BlackboardSync-*-linux-x86_64.tar.gz
cd BlackboardSync-*-linux-x86_64
./install.sh
```

La instalacion es solo para el usuario actual, crea el lanzador del escritorio
y habilita el inicio automatico. Usa `./install.sh --no-autostart` para omitirlo.
Consulta el `README.md` incluido en el paquete para dependencias graficas y
desinstalacion.

[![CI][build-shield]][actions]
[![GitHub Downloads][downloads-shield]][releases]
[![Latest Release Downloads][release-downloads-shield]][stable]
[![Latest Release][latest-shield]][stable]
[![GitHub Stars][stars-shield]][stars]

[actions]: https://github.com/johnbarraza/UPBlackboardSync/actions
[build-shield]: https://img.shields.io/github/actions/workflow/status/johnbarraza/UPBlackboardSync/test.yml?branch=main&label=tests
[downloads-shield]: https://img.shields.io/github/downloads/johnbarraza/UPBlackboardSync/total?label=github%20downloads
[release-downloads-shield]: https://img.shields.io/github/downloads/johnbarraza/UPBlackboardSync/latest/total?label=latest%20release%20downloads
[latest-shield]: https://img.shields.io/github/v/release/johnbarraza/UPBlackboardSync?display_name=tag
[stable]: https://github.com/johnbarraza/UPBlackboardSync/releases/latest
[releases]: https://github.com/johnbarraza/UPBlackboardSync/releases
[stars-shield]: https://img.shields.io/github/stars/johnbarraza/UPBlackboardSync?style=social
[stars]: https://github.com/johnbarraza/UPBlackboardSync/stargazers

## Control remoto via MCP

La app incluye un servidor MCP embebido (puerto `39571`) que arranca automaticamente al abrir BlackboardSync. Permite que Claude u otras herramientas de IA monitoreen y controlen la app remotamente.

Se puede desactivar desde **Preferencias → Remote Control (MCP)**.

[Ver documentacion completa del MCP →](docs/mcp.md)

