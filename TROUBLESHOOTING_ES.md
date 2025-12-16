# Guía de Solución de Problemas - BlackboardSync

## 🔍 Problemas Comunes

### 1. Error: "IncompleteRead" o "Connection broken"

**Síntomas:**
```
urllib3.exceptions.IncompleteRead: IncompleteRead(506746 bytes read, 1004270 more expected)
requests.exceptions.ChunkedEncodingError: ('Connection broken...')
```

**Causas:**
- Archivos grandes que tardan mucho en descargarse
- Conexión de red inestable
- El servidor de Blackboard cierra la conexión prematuramente

**Soluciones aplicadas:**
- ✅ Timeouts aumentados a 5 minutos para archivos grandes
- ✅ Tamaño de chunk aumentado de 1KB a 8KB para mayor eficiencia
- ✅ Los archivos que fallan se reintentarán en el próximo sync
- ✅ Archivos parciales se eliminan automáticamente si falla la descarga

**Qué hacer:**
- El programa automáticamente reintentará descargar el archivo en el siguiente sync
- Verifica tu conexión de red
- Si el problema persiste con un archivo específico, puede que ese archivo esté corrupto en Blackboard

---

### 2. "Session expired" - Sesión expirada

**Síntomas:**
```
User session expired
Session expired - please log in again
```

**Causa:**
Muchas universidades (incluyendo Universidad del Pacífico) **solo permiten una sesión activa a la vez**.

Cuando accedes a Blackboard desde:
- Tu navegador web
- La app móvil de Blackboard
- Otro dispositivo

**La sesión de BlackboardSync se cierra automáticamente**.

**Soluciones aplicadas:**
- ✅ El programa detecta cuando la sesión expira
- ✅ Te solicita volver a autenticarte
- ✅ No marca como error permanente
- ✅ Los archivos descargados antes de expirar la sesión se mantienen

**Qué hacer:**
1. **Opción A (Recomendada):** Deja que BlackboardSync se ejecute solo mientras trabajas, y usa el navegador cuando el programa esté cerrado
2. **Opción B:** Vuelve a iniciar sesión en BlackboardSync después de usar el navegador
3. El programa continuará desde donde quedó, sin redescargar archivos ya descargados

---

### 3. ¿Se vuelven a descargar todos los archivos cada vez?

**Respuesta: NO** ❌

El programa es **incremental**:
- Solo descarga archivos **nuevos** o **modificados**
- Guarda la fecha del último sync en la configuración
- Compara la fecha de modificación de cada archivo en Blackboard
- Si el archivo no ha cambiado desde el último sync, **se omite**

**Ubicación del tracking:**
- Fecha del último sync: `blackboard_sync/sync.py` líneas 244-247
- Verificación de cambios: `blackboard_sync/content/job.py` líneas 16-19

**Ventajas:**
- ✅ Ahorra ancho de banda
- ✅ Sincronización mucho más rápida después del primer sync
- ✅ No sobrescribe archivos que no han cambiado

---

## 📊 Comportamiento del Programa

### Intervalo de Sync
- Por defecto: **30 minutos** (1800 segundos)
- Configurable en `sync.py` línea 58

### Workers Concurrentes
- El programa descarga **múltiples archivos en paralelo**
- Usa `ThreadPoolExecutor` para eficiencia
- Si un archivo falla, los demás continúan descargándose

### Reintentos Automáticos
- ✅ Archivos que fallan se reintentarán en el próximo sync
- ✅ No detiene el sync completo si falla un archivo
- ✅ Logs claros sobre qué archivos fallaron

---

## 🔧 Mejoras Aplicadas

### 1. Timeouts Aumentados
**Archivo:** `blackboard_sync/sync.py` líneas 114-122
```python
# Timeouts configurados:
# - 30 segundos para conectar
# - 300 segundos (5 minutos) para leer datos
```

### 2. Mejor Manejo de Errores
**Archivo:** `blackboard_sync/executor.py` líneas 45-72
- Distingue entre errores críticos (sesión expirada) y temporales (red)
- Solo detiene el sync si la sesión expiró
- Otros errores se logean pero el sync continúa

### 3. Limpieza de Archivos Parciales
**Archivo:** `blackboard_sync/content/base.py` líneas 31-40
- Si falla una descarga, el archivo parcial se elimina automáticamente
- Evita tener archivos corruptos en tu carpeta de descargas

### 4. Chunks Más Grandes
**Archivo:** `blackboard_sync/content/base.py` línea 12
- Aumentado de 1KB a 8KB
- Descarga más eficiente y rápida

---

## 📝 Logs y Debugging

### Ubicación de Logs
Los logs se guardan en:
```
[Tu carpeta de descargas]/log/sync_log_YYYY-MM-DD.log
```

### Niveles de Log
- **INFO:** Operaciones normales (archivos descargados exitosamente)
- **WARNING:** Problemas no críticos (archivos que fallaron pero se reintentarán)
- **ERROR:** Errores que requieren atención

### Mensajes Útiles
```bash
# Descarga exitosa
Successfully downloaded: archivo.pdf

# Archivo falló (se reintentará)
Failed to download archivo.pdf: ChunkedEncodingError

# Múltiples archivos fallaron
3 file(s) failed to download. They will be retried on next sync.

# Sesión expirada
Session expired - please log in again from the application
Your session may have expired because you logged in from another location
```

---

## ⚠️ Advertencias JavaScript (No Críticas)

Estos errores son **normales** y **no afectan la funcionalidad**:

```
js: Uncaught TypeError: Cannot set properties of undefined (setting 'lang')
js: Attempting to get paged collection at /public/v1/lti/placements...
js: Invalid 'X-Frame-Options' header encountered...
```

**Razón:** Son del navegador embebido durante el login. Puedes ignorarlos.

---

## 🆘 Si Nada Funciona

1. **Verifica tu conexión de red**
   ```bash
   ping blackboard.up.edu.pe
   ```

2. **Revisa los logs** en `[carpeta de descargas]/log/`

3. **Reinicia el programa** completamente

4. **Vuelve a autenticarte** en la aplicación

5. **Reporta el problema** en: https://github.com/sanjacob/BlackboardSync/issues
   - Incluye los logs (sin información personal)
   - Menciona tu universidad: Universidad del Pacífico
   - Describe el error específico

---

## 💡 Consejos para Universidad del Pacífico

### Evitar Problemas de Sesión:
1. **Cierra tu navegador** antes de ejecutar BlackboardSync
2. **O** ejecuta BlackboardSync cuando no necesites el navegador
3. El programa sincroniza cada 30 minutos, así que puede correr en segundo plano

### Archivos Grandes:
- El programa ahora soporta archivos de hasta **cientos de MB**
- Timeout configurado para 5 minutos por archivo
- Si tienes videos grandes, estos **no se descargan** (configuración por defecto)

### Primera Ejecución:
- La primera vez descargará **todos** los archivos de tus cursos
- Puede tomar varios minutos dependiendo de cuánto contenido tengas
- Ejecuciones subsecuentes serán mucho más rápidas

---

**Última actualización:** 2025-12-16
**Versión:** BlackboardSync con mejoras de timeout y manejo de errores
