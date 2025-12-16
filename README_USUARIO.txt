================================================================================
               BlackboardSync - Descarga Automática de Blackboard
================================================================================

¿QUÉ ES BLACKBOARDSYNC?
-----------------------
BlackboardSync descarga automáticamente todo tu contenido de Blackboard Learn
(slides, PDFs, laboratorios, etc.) a tu computadora. Se ejecuta en segundo
plano y sincroniza cada 30 minutos.


CARACTERÍSTICAS
---------------
✓ Descarga automática e incremental (solo archivos nuevos)
✓ Compatible con 60+ universidades
✓ Interfaz gráfica sencilla
✓ Sin necesidad de instalar Python
✓ Funciona en segundo plano


INSTALACIÓN
-----------
1. Descomprime el archivo ZIP en cualquier carpeta
2. Ejecuta "BlackboardSync.exe"
3. ¡Eso es todo! No requiere instalación adicional


PRIMER USO
----------
1. Al abrir el programa, selecciona tu universidad de la lista
   (Ejemplo: Universidad del Pacífico)

2. Haz clic en "Login"
   - Se abrirá una ventana del navegador
   - Inicia sesión con tus credenciales de Blackboard
   - Cierra la ventana cuando termines

3. Selecciona la carpeta donde quieres guardar los archivos
   (Ejemplo: C:\Users\TuNombre\Documents\Blackboard)

4. El programa comenzará a descargar tus archivos
   - Primera vez: descargará TODO (puede tomar tiempo)
   - Siguientes veces: solo archivos nuevos (rápido)


USO NORMAL
----------
- El programa sincroniza automáticamente cada 30 minutos
- Puedes dejarlo ejecutándose en segundo plano
- Minimízalo a la bandeja del sistema
- Para forzar una sincronización: haz clic en "Sync Now"


IMPORTANTE - SESIONES ÚNICAS
-----------------------------
⚠ Blackboard solo permite UNA sesión activa a la vez

Si inicias sesión en Blackboard desde:
  • Tu navegador web
  • La app móvil
  • Otro dispositivo

→ BlackboardSync se desconectará automáticamente

SOLUCIÓN:
  • Usa BlackboardSync cuando NO necesites el navegador
  • O vuelve a iniciar sesión en BlackboardSync después de usar el navegador


¿SE VUELVEN A DESCARGAR TODOS LOS ARCHIVOS?
-------------------------------------------
NO. El programa es inteligente:

✓ Solo descarga archivos NUEVOS o MODIFICADOS
✓ Los archivos existentes NO se re-descargan
✓ Ahorra tiempo y ancho de banda

Primera descarga: ~10-30 minutos (dependiendo de tu contenido)
Siguientes descargas: ~1-5 minutos (solo archivos nuevos)


SOLUCIÓN DE PROBLEMAS
----------------------

Problema: "Session expired"
---------------------------
Causa: Iniciaste sesión en Blackboard desde otro lugar
Solución: Vuelve a hacer login en BlackboardSync


Problema: "Download error" o "Connection broken"
-------------------------------------------------
Causa: Conexión de red inestable o archivo muy grande
Solución:
  • El archivo se reintentará automáticamente en 30 minutos
  • Verifica tu conexión de red
  • Si persiste, ese archivo puede estar corrupto en Blackboard


Problema: El programa se cierra inesperadamente
------------------------------------------------
Solución:
  • Ejecuta como administrador (clic derecho → "Run as administrator")
  • Verifica tu antivirus no esté bloqueando el programa
  • Revisa los logs en: [carpeta de descargas]/log/


Problema: Antivirus marca el programa como amenaza
---------------------------------------------------
Es un FALSO POSITIVO común con programas compilados con PyInstaller

Solución:
  • Agrega BlackboardSync.exe a excepciones del antivirus
  • El código fuente está disponible en:
    https://github.com/sanjacob/BlackboardSync


CARPETAS Y ARCHIVOS
-------------------
Después de la primera sincronización, verás:

Tu_Carpeta_Elegida/
├── Nombre_Curso_1/
│   ├── Semana 1/
│   │   ├── Slides.pdf
│   │   └── Laboratorio.docx
│   └── Semana 2/
│       └── ...
├── Nombre_Curso_2/
│   └── ...
└── log/
    └── sync_log_2025-12-16.log


TIPOS DE ARCHIVO SOPORTADOS
----------------------------
✓ Documentos (.pdf, .docx, .pptx, .xlsx, etc.)
✓ Imágenes (.png, .jpg, etc.)
✓ Archivos comprimidos (.zip, .rar, etc.)
✓ Enlaces web (se guardan como archivos .html)
✓ Descripciones de contenido (como archivos .html)

✗ Videos (no se descargan por defecto - muy grandes)


CONFIGURACIÓN AVANZADA
-----------------------
• Intervalo de sincronización: 30 minutos (no modificable en la GUI)
• Año mínimo de cursos: Configurable en el asistente inicial
• Ubicación de logs: [carpeta de descargas]/log/


ACTUALIZACIONES
---------------
Para actualizar a una nueva versión:
1. Descarga la nueva versión
2. Descomprime en una nueva carpeta
3. Al ejecutar, apunta a la MISMA carpeta de descargas
4. No se re-descargarán los archivos existentes


PRIVACIDAD Y SEGURIDAD
----------------------
✓ Tus credenciales NO se almacenan en el programa
✓ Solo se guarda una "sesión" temporal (como cookies del navegador)
✓ Toda la comunicación es con los servidores de tu universidad
✓ El código es 100% open source y auditable


DESINSTALAR
-----------
1. Cierra el programa
2. Elimina la carpeta donde descomprimiste BlackboardSync
3. Opcionalmente, elimina la carpeta de descargas si no la necesitas


LICENCIA
--------
BlackboardSync es Software Libre bajo licencia GPL v2

Copyright (C) 2024, Jacob Sánchez Pérez

Esto significa:
  ✓ Libre para usar, modificar y distribuir
  ✓ Código fuente disponible públicamente
  ✓ Sin garantías (usa bajo tu propio riesgo)


CRÉDITOS
--------
Desarrollador original: Jacob Sánchez (jacobszpz@protonmail.com)
Página web: https://bbsync.app
Código fuente: https://github.com/sanjacob/BlackboardSync
Reportar problemas: https://github.com/sanjacob/BlackboardSync/issues

Mejoras de estabilidad y manejo de errores: Diciembre 2024


SOPORTE
-------
Para ayuda adicional:
  • Lee TROUBLESHOOTING_ES.md (si está incluido)
  • Visita: https://github.com/sanjacob/BlackboardSync
  • Reporta bugs: https://github.com/sanjacob/BlackboardSync/issues


================================================================================
                    ¡Gracias por usar BlackboardSync!
================================================================================

Versión: 2024.12 (con mejoras de timeout y manejo de errores)
