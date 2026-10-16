# Informe de Estado del Proyecto: Water Management Network
**Asignatura:** Sistemas Distribuidos 2026/2027  
**Fecha de actualización:** Viernes, 16 de octubre de 2026 (11:50h)  
**Fecha objetivo de cierre:** Viernes, 23 de octubre de 2026 (Entrega oficial: semana del 26 de octubre)  
**Equipo:** Persona A (Héctor — Central y Nube) · Persona B (Julián — Estaciones, Operario y Laboratorio)

---

## 1. Resumen Ejecutivo a Fecha de Hoy (16 de Octubre)

En los últimos dos días (14 al 16 de octubre) el proyecto ha dado un salto importante, pasando de un repositorio vacío a tener **toda la capa de comunicaciones por Sockets TCP, persistencia SQLite y autenticación Monitor $\leftrightarrow$ Central operativa**.

* **Lo que ya funciona:**
  1. Arquitectura de protocolos de sockets en `/common/protocol/` con dos implementaciones intercambiables ([`StandardLRCProtocol`](file:///Users/julianhinojosagil/Documents/Dev/water-management/common/protocol/standard_lrc.py#L20-L128) con `<STX><DATA><ETX><LRC>` y [`LineDelimitedProtocol`](file:///Users/julianhinojosagil/Documents/Dev/water-management/common/protocol/line_delim.py#L6-L44)) junto con sus tests y benchmarks ([`test_protocol.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/tests/test_protocol.py), [`benhmark_protocol.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/tests/benhmark_protocol.py)).
  2. Núcleo de `WM_Central` ([`WM_Central.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/central/WM_Central.py), [`db.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/central/database/db.py), [`state.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/central/src/state.py), [`socket_server.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/central/src/socket_server.py)): inicializa SQLite, resetea las estaciones a `DISCONNECTED` al arrancar, mantiene el estado en memoria de forma *thread-safe* y atiende por sockets las peticiones `AUTH`, `LEAK` y `RECOVERED`.
  3. Primera versión funcional de [`WM_WS_M.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/ws/monitor/WM_WS_M.py) (en tu entorno local, pendiente de `git add`/`commit`): conecta con `WM_Central`, realiza el handshake y autentica la estación de riego.
* **Principal cuello de botella actual:**
  * **La capa de Apache Kafka está al 0 %** ([`common/topics.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/common/topics.py), [`common/messages.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/common/messages.py) y [`central/src/kafka_handlers.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/central/src/kafka_handlers.py) son archivos de 0 bytes). Mañana **17 de octubre** vence el Hito 3 del calendario (*"Un riego completo de principio a fin en local"*).

---

## 2. Auditoría de Ramas Git y Entorno Local

### 2.1. Estado de las Ramas (Locales vs. Remotas en GitHub)

| Rama | Último Commit | Estado / Sincronización | Contenido Principal |
| :--- | :--- | :--- | :--- |
| **`origin/main`** / **`main`** | `e7d3646` (23 sep) | Sincronizadas | Esqueleto inicial intacto (aún no se ha volcado `dev` a `main`). |
| **`origin/dev`** | `5a1a456` (16 oct, 11:06) | Tu rama local `dev` está 3 commits por detrás (`18ec3cb`). | Contiene la fusión de PR #1 (protocolos de sockets de Julián), el núcleo de Central de Héctor y el PR #3 (selección dinámica de protocolo y eliminación de `common/protocol.py` duplicado). |
| **`origin/dev-julian`** | `859a82b` (16 oct, 11:07) | Tu rama local `dev-julian` (`06206e6`) tiene **exactamente el mismo código** (solo le faltan 2 commits de merge sin cambios de ficheros). | Todo el paquete `common/protocol/`, suite `tests/` y refactor de `WM_Central` / `socket_server` para elegir protocolo (`lrc` o `line`). |
| **`origin/dev-hector`** | `3b090a2` (16 oct, 11:46) | Tu copia local `dev-hector` sigue en `e7d3646` (23 commits por detrás). | Héctor acaba de hacer merge de `dev` en su rama (`3b090a2`), más un commit previo (`30d1095`) donde eliminó comentarios de cabecera en 4 ficheros de `central/`. |

### 2.2. Archivos Locales sin Seguimiento (*Untracked* en tu Workspace)
En tu directorio de trabajo actual (rama `dev-julian`) existen dos archivos nuevos que aún no se han subido a Git:
1. **[`ws/monitor/WM_WS_M.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/ws/monitor/WM_WS_M.py)** (69 líneas): Implementación inicial del Monitor de la estación de riego (conexión y autenticación contra Central).
2. **`central/database/wm.db`**: Base de datos SQLite generada al probar `WM_Central.py`.
   > [!TIP]
   > En [`.gitignore`](file:///Users/julianhinojosagil/Documents/Dev/water-management/.gitignore#L12-L15) están ignorados `*.sqlite` y `*.sqlite3`, pero no `*.db`. Conviene añadir `*.db` a `.gitignore` para no subir accidentalmente la base de datos local al repositorio.

---

## 3. Estado Detallado por Componente frente al Enunciado

### 3.1. Módulo Compartido (`/common` y `/tests`) — *Tarea Conjunta*

| Archivo | Estado | Análisis Técnico |
| :--- | :---: | :--- |
| [`common/protocol/base.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/common/protocol/base.py) | **100 %** | Define la interfaz [`BaseProtocol`](file:///Users/julianhinojosagil/Documents/Dev/water-management/common/protocol/base.py#L6-L34) con métodos de sesión (`init_connection`, `accept_connection`, `close_connection`) y mensajería (`send_request`, `receive_request`, `send_response`). |
| [`common/protocol/standard_lrc.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/common/protocol/standard_lrc.py) | **100 %** | Implementa [`StandardLRCProtocol`](file:///Users/julianhinojosagil/Documents/Dev/water-management/common/protocol/standard_lrc.py#L20-L128) fiel al diagrama de la pág. 12 del PDF: saludo `ENQ` $\rightarrow$ `ACK`, empaquetado `<STX><DATA><ETX><LRC>` con XOR byte a byte ([`compute_lrc`](file:///Users/julianhinojosagil/Documents/Dev/water-management/common/protocol/standard_lrc.py#L12-L17)), confirmación `ACK`/`NACK` y despedida `EOT`. |
| [`common/protocol/line_delim.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/common/protocol/line_delim.py) | **100 %** | Implementa [`LineDelimitedProtocol`](file:///Users/julianhinojosagil/Documents/Dev/water-management/common/protocol/line_delim.py#L6-L44) delimitado por `\n` para comparar rendimiento frente a LRC. |
| [`tests/test_protocol.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/tests/test_protocol.py) y [`benhmark_protocol.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/tests/benhmark_protocol.py) | **100 %** | Pruebas funcionales cliente/servidor en hilos y benchmark de latencia y throughput con 2000 peticiones. |
| [`common/topics.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/common/topics.py) | **0 % (Vacío)** | **Crítico:** Falta definir las constantes de topics de Kafka (ej. peticiones de riego, comandos a WS, telemetría, notificaciones a FO). |
| [`common/messages.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/common/messages.py) | **0 % (Vacío)** | **Crítico:** Falta definir el contrato de constructores/validadores JSON para los eventos de Kafka. |

---

### 3.2. Core System (`/central`) — *Persona A (Héctor)*

| Archivo | Estado | Análisis Técnico |
| :--- | :---: | :--- |
| [`central/database/db.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/central/database/db.py) | **100 %** | Crea tablas `operators` y `stations` ([`ini_bd`](file:///Users/julianhinojosagil/Documents/Dev/water-management/central/database/db.py#L21-L32)). Gestiona alta de operarios, registro de estaciones, actualización de estados y reseteo masivo a `DISCONNECTED` ([`desc_todas`](file:///Users/julianhinojosagil/Documents/Dev/water-management/central/database/db.py#L119-L126)). Abre una conexión por operación para evitar conflictos entre hilos en SQLite. |
| [`central/src/state.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/central/src/state.py) | **100 %** | Caché en memoria protegida con `threading.Lock` y actualización *write-through* a BD. Contempla los 5 estados del enunciado: `ACTIVE`, `WATERING`, `LEAK`, `OUT_OF_SERVICE`, `DISCONNECTED`. Incluye [`act_riego`](file:///Users/julianhinojosagil/Documents/Dev/water-management/central/src/state.py#L97-L105) para caudal, volumen y operario. |
| [`central/src/socket_server.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/central/src/socket_server.py) | **95 %** | Servidor TCP multihilo con límite de 50 monitores concurrentes (`BoundedSemaphore`). Procesa `AUTH#id#ubicacion`, `LEAK#id` y `RECOVERED#id`. Cuando un Monitor cierra el socket o cae, el bloque `finally` pasa la estación a `DISCONNECTED`. *(Falta: cuando llega `LEAK#id` durante un riego en curso, notificar por Kafka el corte inmediato a todos los módulos según el punto 9 del enunciado).* |
| [`central/WM_Central.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/central/WM_Central.py) | **60 %** | Lee argumentos CLI (`<puerto> [ip_kafka:puerto_kafka] [ruta_bd] [protocolo]`), inicializa BD con 3 operarios (`OP01`..`OP03`), fuerza todas las estaciones a `DISCONNECTED` al arrancar y lanza el servidor de sockets. Falta arrancar los hilos de Kafka y del panel web (línea 73). |
| [`central/src/kafka_handlers.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/central/src/kafka_handlers.py) | **0 % (Vacío)** | Pendiente: consumidores de peticiones de FO y telemetría de Engine, y productores de órdenes/notificaciones. |
| [`central/src/commands.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/central/src/commands.py) | **0 % (Vacío)** | Pendiente: órdenes arbitrarias desde Central (punto 11 del enunciado: iniciar riego, bloquear WS a `OUT_OF_SERVICE` naranja, activar WS a `ACTIVE` verde). |
| [`central/src/panel/`](file:///Users/julianhinojosagil/Documents/Dev/water-management/central/src/panel/app.py) (`app.py`, `index.html`, `style.css`) | **0 % (Vacíos)** | Pendiente: cuadro de mandos web con los 5 colores/estados, parpadeo en verde al regar, caudal, volumen e ID de operario. |
| [`central/Dockerfile`](file:///Users/julianhinojosagil/Documents/Dev/water-management/central/Dockerfile) y [`requirements.txt`](file:///Users/julianhinojosagil/Documents/Dev/water-management/central/requirements.txt) | **0 % (Vacíos)** | Pendiente para el despliegue en Railway. |

---

### 3.3. Estaciones (`/ws`) y Operarios (`/operator`) — *Persona B (Julián)*

| Módulo / Archivo | Estado | Lo que ya está hecho | Lo que falta por implementar |
| :--- | :---: | :--- | :--- |
| **Monitor (`WM_WS_M`)**<br>[`ws/monitor/WM_WS_M.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/ws/monitor/WM_WS_M.py) | **45 %**<br>*(En local, sin commitear)* | <ul><li>Parseo de argumentos obligatorios (`<puerto_engine> <ip_central:puerto_central> <id_ws>`) y opcionales (`[ubicacion] [protocolo]`).</li><li>Conexión TCP a `WM_Central`, handshake `init_connection`, envío de `AUTH#id_ws#ubicacion` y cierre limpio con `EOT`.</li></ul> | <ul><li>Abrir servidor de sockets local en `<puerto_engine>` para aceptar a `WM_WS_E`.</li><li>Bucle de comprobación de salud cada **1 segundo** hacia `WM_WS_E` (ej. `PING` $\rightarrow$ `OK` / `KO`).</li><li>Si `WM_WS_E` responde `KO` o se desconecta, enviar `LEAK#<id_ws>` a `WM_Central`.</li><li>Cuando `WM_WS_E` se recupere, enviar `RECOVERED#<id_ws>` a `WM_Central`.</li></ul> |
| **Engine (`WM_WS_E`)**<br>`ws/engine/WM_WS_E.py` | **0 %**<br>*(No creado)* | Solo existe `ws/engine/.gitkeep`. | <ul><li>Recibir por CLI `<ip_kafka:puerto_kafka> <ip_monitor:puerto_monitor>` (y el ID de WS o recibirlo del Monitor al conectar).</li><li>Conectar por socket al Monitor `WM_WS_M` y responder cada segundo al ping de salud (`OK` o `KO`).</li><li>Hilo/lectura de teclado en tiempo real para alternar estado de avería (`KO`) y recuperación (`OK`), y opción de menú para finalizar riego manualmente o regar manualmente.</li><li>Consumidor/Productor Kafka: recibir orden de activación, abrir electroválvula, emitir telemetría cada **1 segundo** (caudal L/min y volumen acumulado L), y detener riego por límite de tiempo, menú o fuga enviando resumen final.</li></ul> |
| **Field Operator (`WM_FO`)**<br>`operator/src/WM_FO.py` | **0 %**<br>*(No creado)* | Solo existe `operator/src/.gitkeep`. | <ul><li>Recibir por CLI `<ip_kafka:puerto_kafka> <id_operador>`.</li><li>Consultar/mostrar estaciones disponibles.</li><li>Modo manual: solicitar activación de riego en una WS.</li><li>Modo automático por **fichero**: leer servicios de un archivo, enviar el primero a Central, esperar su conclusión (éxito o fracaso), **esperar 4 segundos** y solicitar el siguiente.</li><li>Mostrar en pantalla todos los pasos de validación, telemetría en vivo de su WS y resumen final del riego.</li></ul> |
| **Dockerfiles Lab y Pruebas** | **0 %** | — | `ws/Dockerfile`, `operator/Dockerfile`, `docker-compose.yml` local y script generador de `<DNI>SD_Test.log`. |

---

## 4. Seguimiento del Calendario e Hitos del Equipo

```
[✅ COMPLETADO]  7-9 Oct   : Repo GitHub + Protocolo de Sockets en /common (StandardLRC + LineDelim)
[🟡 AL 75%]      10-13 Oct : Sockets y Auth (Servidor Central + BD + Estado listos; Monitor conecta y autentica; falta ping Engine-Monitor y Panel)
[🔴 EN RIESGO]   14-17 Oct : Flujo de riego con Kafka (HOY es 16 Oct: topics.py y messages.py siguen vacíos)
[⏳ PRÓXIMO]     18-20 Oct : Funcionalidad completa (Fugas en riego, órdenes globales, FO modo fichero)
[⏳ PRÓXIMO]     21-22 Oct : Despliegue Railway + 2 PCs Laboratorio con Docker
[⏳ META]        23 Oct    : Cierre, log <DNI>SD_Test.log, carpeta prompts IA y memoria
```

### Evaluación de Hitos de Control (Sección 5 del Plan de Héctor):
1. **Fin 9 oct — *Contrato de mensajes escrito***:
   * **Sockets:** Cerrado (`AUTH#id#ubicacion`, `LEAK#id`, `RECOVERED#id` sobre `StandardLRCProtocol`).
   * **Kafka:** **Pendiente**. Es urgente rellenar [`common/topics.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/common/topics.py) y [`common/messages.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/common/messages.py) hoy mismo para que Héctor pueda programar [`kafka_handlers.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/central/src/kafka_handlers.py) y tú puedas programar `WM_WS_E` y `WM_FO`.
2. **Fin 13 oct — *Una WS se registra en Central y aparece en el panel***:
   * Registro en Central y persistencia en SQLite: **Conseguido** (al ejecutar `WM_Central.py` y `WM_WS_M.py`, la estación pasa de `DISCONNECTED` a `ACTIVE`).
   * Visualización en el Panel Web: **Pendiente** (parte de Héctor en `central/src/panel/`).
3. **Fin 17 oct — *Un riego completo de principio a fin en local***:
   * **En riesgo inmediato** (vence mañana sábado 17 de octubre). Requiere cerrar hoy el contrato de Kafka y mañana los manejadores en `WM_Central`, `WM_WS_E` y `WM_FO`.

---

## 5. Observaciones Técnicas Importantes Detectadas en el Código

1. **Coordinación de `origin/dev-hector` vs `origin/dev`:**
   * En el commit `30d1095` y merge `3b090a2` (hace unos minutos), Héctor borró algunos bloques de comentarios explicativos al principio de `WM_Central.py`, `db.py`, `socket_server.py` y `state.py`. No afecta a la lógica funcional, pero conviene que actualices tu rama local con `git pull origin dev-julian` antes de subir nuevos cambios.
2. **Paso del ID de la estación de `WM_WS_M` a `WM_WS_E`:**
   * El enunciado (pág. 10) especifica sobre `WM_WS_E`: *"La WS quedará asignada con el ID recibido en la línea de parámetros del WM_WS_M y cuya validez deberá ser confirmada por WM_Central en el proceso de autenticación"*.
   * Por tanto, cuando `WM_WS_E` se conecte por socket a `WM_WS_M`, el Monitor puede enviarle el `id_ws` (por ejemplo en el primer mensaje o saludo de control, o dentro del comando `PING#<id_ws>`) para que `WM_WS_E` no tenga que recibir el ID por consola y sepa a qué topic/ID de estación responder en Kafka.
3. **Corte inmediato de riego por fuga:**
   * Actualmente en [`socket_server.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/central/src/socket_server.py#L160-L162), cuando Central recibe `LEAK#id`, solo llama a `state.fij_estado(id_estacion, state.LEAK)`. Cuando conectéis Kafka, si la estación estaba en estado `WATERING`, tanto el Engine como Central deben abortar el riego inmediatamente y notificar al operario (punto 9 del enunciado).
4. **Registro de Prompts de IA:**
   * Aún no se ha creado la carpeta/documento de prompts de IA en el repositorio.

---

## 6. Plan de Acción Recomendado para Hoy (16 de Octubre)

1. **Sincronizar e ignorar archivos temporales:**
   * Añadir `*.db` a [`.gitignore`](file:///Users/julianhinojosagil/Documents/Dev/water-management/.gitignore) y eliminar `central/database/wm.db`.
   * Hacer `git pull origin dev-julian` para traer los commits de merge `5a1a456` y `859a82b`.
2. **Completar `ws/monitor/WM_WS_M.py` (100 % del Monitor):**
   * Añadir el servidor de sockets en `<puerto_engine>` para que conecte `WM_WS_E`.
   * Implementar el bucle de ping cada 1 segundo (`PING#<id_ws>`) y el envío automático de `LEAK#<id_ws>` y `RECOVERED#<id_ws>` a `WM_Central`.
   * Subir `WM_WS_M.py` a `dev-julian`.
3. **Definir el Contrato de Kafka en `/common` (Prioridad Máxima Conjunta):**
   * Rellenar [`common/topics.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/common/topics.py) y [`common/messages.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/common/messages.py) y hacer PR a `dev` para desbloquear el flujo de riego de este fin de semana.
4. **Implementar `ws/engine/WM_WS_E.py` y `operator/src/WM_FO.py`.**
