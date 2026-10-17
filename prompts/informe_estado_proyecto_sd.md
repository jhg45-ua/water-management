# Informe de Estado del Proyecto: Water Management Network
**Asignatura:** Sistemas Distribuidos 2026/2027  
**Fecha de actualización:** Sábado, 17 de octubre de 2026 (20:07h)  
**Fecha objetivo de cierre:** Viernes, 23 de octubre de 2026 (Entrega oficial: semana del 26 de octubre)  
**Equipo:** Persona A (Héctor — Central y Nube) · Persona B (Julián — Estaciones, Operario y Laboratorio)

---

## 1. Resumen Ejecutivo a Fecha de Hoy (17 de Octubre — 20:07h)

Hoy se ha producido un **avance masivo en el repositorio remoto (`origin/dev` y `origin/dev-hector`)**: Héctor ha subido **18 nuevos commits** (hasta `085d994`) con los que **toda la parte de `WM_Central`, el contrato de Kafka en `/common`, el Panel Web en Flask y la Dockerización de Central + Kafka están al 100 % implementados**.

* **Lo que ya está 100 % implementado en el repositorio:**
  1. **Contrato completo en `/common`**:
     * **Sockets (`/common/protocol/`)**: [`BaseProtocol`](file:///Users/julianhinojosagil/Documents/Dev/water-management/common/protocol/base.py), [`StandardLRCProtocol`](file:///Users/julianhinojosagil/Documents/Dev/water-management/common/protocol/standard_lrc.py) (`<STX><DATA><ETX><LRC>`) y [`LineDelimitedProtocol`](file:///Users/julianhinojosagil/Documents/Dev/water-management/common/protocol/line_delim.py), con tests y benchmarks.
     * **Kafka (`common/topics.py` y `common/messages.py` en `origin/dev`)**: Definidos los 4 topics (`wm.fo.requests`, `wm.fo.notifications`, `wm.ws.commands`, `wm.ws.telemetry`) y todos los constructores/serializadores JSON (`msj_pet`, `msj_notif`, `msj_orden`, `msj_telem`).
  2. **Sistema Central completo (`/central` en `origin/dev`)**:
     * Persistencia SQLite (`db.py`) y caché de estado *thread-safe* con cálculo de resúmenes de riego (`state.py`).
     * Servidor de sockets (`socket_server.py`) conectado con Kafka para cortar riegos automáticamente ante fugas (`LEAK`) o desconexiones.
     * Manejadores de Kafka (`kafka_handlers.py`) usando `kafka-python` con reconexión automática, reserva de estaciones, validación de operarios y retransmisión de telemetría.
     * Menú interactivo de consola (`commands.py`) y **Panel Web en Flask** (`panel/app.py` + `templates/index.html`) con tarjetas en los 5 colores del enunciado, parpadeo CSS en verde durante el riego y botones para órdenes individuales o globales (`ALL`).
     * `central/Dockerfile`, `central/requirements.txt` (`kafka-python`, `flask`) y `central/docker-compose.yml` (con `apache/kafka:3.8.1` en modo KRaft + `central`).
  3. **Monitor de Estación completo ([`ws/monitor/WM_WS_M.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/ws/monitor/WM_WS_M.py) en `dev-julian`)**:
     * Autenticación contra Central, servidor local para Engine, ping cada 1s (`CHECK_HEALTH`), alerta `LEAK#<id_ws>` y recuperación `RECOVERED#<id_ws>`.

* **Lo que queda pendiente (100 % desbloqueado, lado Persona B — Julián):**
  1. Sincronizar ramas (`origin/dev` $\leftrightarrow$ `dev-julian`).
  2. Implementar **`ws/engine/WM_WS_E.py`** (Engine).
  3. Implementar **`operator/src/WM_FO.py`** (Field Operator).
  4. Crear los Dockerfiles de laboratorio (`ws/Dockerfile` y `operator/Dockerfile`) y el script generador del log `<DNI>SD_Test.log`.

---

## 2. Auditoría de Ramas Git y Sincronización

| Rama | Último Commit | Estado / Sincronización | Contenido Principal |
| :--- | :--- | :--- | :--- |
| **`origin/main`** / **`main`** | `e7d3646` (23 sep) | Sincronizadas | Esqueleto inicial intacto. |
| **`origin/dev`** y **`origin/dev-hector`** | `085d994` (17 oct) | **18 commits por delante** de tu rama `dev-julian` (y tu `dev` local está 23 commits por detrás). | Contiene todo el cierre de `central/` (`kafka_handlers.py`, `commands.py`, `panel/`, `Dockerfile`, `docker-compose.yml`) y el contrato Kafka (`common/topics.py`, `common/messages.py`). **Aún no tiene tu commit `3ae3303` (`WM_WS_M.py`)**. |
| **`origin/dev-julian`** / **`dev-julian`** | `3ae3303` (16 oct) | Sincronizadas entre sí, pero **aún no tienen los 18 commits nuevos de `origin/dev`**. | Tiene [`ws/monitor/WM_WS_M.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/ws/monitor/WM_WS_M.py) y [`prompts/informe_estado_proyecto_sd.md`](file:///Users/julianhinojosagil/Documents/Dev/water-management/prompts/informe_estado_proyecto_sd.md). |

> [!IMPORTANT]
> **Acción inmediata en Git:** Tu rama `dev-julian` y `origin/dev` han divergido sin conflictos (tú editaste `ws/monitor/` y `prompts/`; Héctor editó `common/topics.py`, `common/messages.py` y `central/`). Debes hacer `git merge origin/dev` en tu rama `dev-julian` para disponer localmente de `topics.py`, `messages.py` y todo el módulo `central/` actualizado, y después subir/mezclar `dev-julian` en `dev`.

---

## 3. Especificación del Contrato Kafka (Ya implementado en `origin/dev`)

Para programar `WM_WS_E.py` y `WM_FO.py`, debes usar directamente la librería **`kafka-python`** y las funciones que Héctor ha dejado listas en `common/topics.py` y `common/messages.py`:

### 3.1. Topics (`common/topics.py`)
* `topics.PETICIONES = "wm.fo.requests"` — Operario (`WM_FO`) $\rightarrow$ Central.
* `topics.NOTIF_FO = "wm.fo.notifications"` — Central $\rightarrow$ Operario (`WM_FO`).
* `topics.ORDENES = "wm.ws.commands"` — Central $\rightarrow$ Engine (`WM_WS_E`).
* `topics.TELEMETRIA = "wm.ws.telemetry"` — Engine (`WM_WS_E`) $\rightarrow$ Central.

### 3.2. Mensajes JSON (`common/messages.py`)

| Dirección | Función constructora | Estructura JSON generada |
| :--- | :--- | :--- |
| **FO $\rightarrow$ Central** | `msj_pet(operario, ws, duracion)` | `{"type": "REQUEST", "operator": "OP01", "ws": "WS01", "duration": 30}` |
| **Central $\rightarrow$ FO** | `msj_notif(operario, ws, evento, texto, caudal, volumen)` | `{"type": "NOTIFY", "operator": "OP01", "ws": "WS01", "event": "RECEIVED\|AUTHORIZED\|DENIED\|PROGRESS\|FINISHED\|LEAK_STOP", "text": "...", "flow": 10, "volume": 50}` |
| **Central $\rightarrow$ Engine** | `msj_orden(ws, accion, operario, duracion)` | `{"type": "COMMAND", "ws": "WS01\|ALL", "action": "START\|STOP\|BLOCK\|ACTIVATE", "operator": "OP01", "duration": 30}` |
| **Engine $\rightarrow$ Central** | `msj_telem(ws, operario, caudal, volumen, final)` | `{"type": "TELEMETRY", "ws": "WS01", "operator": "OP01", "flow": 12.5, "volume": 25.0, "final": false\|true}` |

* **Serialización:** `messages.a_bytes(diccionario)` para enviar por `KafkaProducer` y `messages.de_bytes(registro.value)` al recibir en `KafkaConsumer`.

---

## 4. Estado Detallado por Componente frente al Enunciado

### 4.1. Módulo Compartido (`/common` y `/tests`) — **100 % Completado**
* `common/protocol/` (`base.py`, `standard_lrc.py`, `line_delim.py`): **100 %**.
* `tests/` (`test_protocol.py`, `benhmark_protocol.py`): **100 %**.
* `common/topics.py` y `common/messages.py` (en `origin/dev`): **100 %**.

### 4.2. Core System (`/central`) — *Persona A (Héctor)* — **100 % Completado en código**
* `central/database/db.py`: **100 %** (SQLite para `operators` y `stations`).
* `central/src/state.py`: **100 %** (reservas de riego `res_riego`, actualización de caudal/volumen `act_riego`, cierre y cálculo de resumen `fin_riego`, bloqueo/activación `cambiar_si`).
* `central/src/socket_server.py`: **100 %** (integrado con `kafka_handlers.estacion_con_fuga` y `estacion_desconectada`).
* `central/src/kafka_handlers.py`: **100 %** (productor y consumidores de `wm.fo.requests` y `wm.ws.telemetry` con reintentos).
* `central/src/commands.py`: **100 %** (menú interactivo en consola y soporte para `ALL`).
* `central/src/panel/` (`app.py`, `templates/index.html`): **100 %** (panel web Flask con refresco cada 1s, 5 estados con colores y parpadeo en riego, y disparo de órdenes).
* `central/Dockerfile`, `central/requirements.txt`, `central/docker-compose.yml`: **100 %**.
  > [!NOTE]
  > **Detalle en `central/docker-compose.yml`:** El archivo está dentro de `central/` pero define `context: .` y `dockerfile: central/Dockerfile`. Para ejecutarlo correctamente, debe lanzarse desde la raíz del repositorio indicando `--project-directory .`:
  > `docker compose -f central/docker-compose.yml --project-directory . up --build`

### 4.3. Estaciones (`/ws`) y Operarios (`/operator`) — *Persona B (Julián)*

| Módulo / Archivo | Estado | Lo que ya está hecho | Lo que falta por implementar |
| :--- | :---: | :--- | :--- |
| **Monitor (`WM_WS_M`)**<br>[`ws/monitor/WM_WS_M.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/ws/monitor/WM_WS_M.py) | **95 %** | <ul><li>Conexión y `AUTH` con Central.</li><li>Servidor local para el Engine y bucle `vigilar_engine` cada 1s.</li><li>Envío de `LEAK#<id_ws>` y `RECOVERED#<id_ws>`.</li></ul> | <ul><li>Cambiar `"CHECK_HEALTH"` en la línea 58 por `f"CHECK_HEALTH#{id_ws}"` para que `WM_WS_E` aprenda automáticamente su `id_ws` al conectarse al Monitor.</li></ul> |
| **Engine (`WM_WS_E`)**<br>`ws/engine/WM_WS_E.py` | **0 %**<br>*(Siguiente paso)* | Solo existe `ws/engine/.gitkeep`. | <ul><li>Recibir por CLI `<ip_kafka:puerto_kafka> <ip_monitor:puerto_monitor> [protocolo]`.</li><li>Conectar por socket al Monitor, hacer `init_connection`, recibir `CHECK_HEALTH#<id_ws>` y responder `"OK"` o `"KO"`.</li><li>Consumir `topics.ORDENES` (`"wm.ws.commands"`): atender `START`, `STOP`, `BLOCK`, `ACTIVATE` dirigidos a su `id_ws` o a `"ALL"`.</li><li>Durante el riego: cada **1 segundo** enviar `messages.msj_telem(..., final=False)` a `topics.TELEMETRIA` y al cumplir `duration` (o parar desde menú) enviar `final=True`.</li><li>Si el usuario pulsa tecla para simular fuga (`KO`), cortar riego en curso y responder `"KO"` al Monitor hasta que pulse tecla de recuperar (`OK`).</li></ul> |
| **Field Operator (`WM_FO`)**<br>`operator/src/WM_FO.py` | **0 %**<br>*(Siguiente paso)* | Solo existe `operator/src/.gitkeep`. | <ul><li>Recibir por CLI `<ip_kafka:puerto_kafka> <id_operador> [fichero_servicios]`.</li><li>Consumir en un hilo `topics.NOTIF_FO` (`"wm.fo.notifications"`) filtrando `msg["operator"] == id_operador`, mostrando `RECEIVED`, `AUTHORIZED`, `DENIED`, `PROGRESS` (caudal y volumen), `FINISHED` y `LEAK_STOP`.</li><li>Modo manual: pedir `ws` y `duracion` por teclado y publicar `messages.msj_pet(...)` en `topics.PETICIONES`.</li><li>Modo fichero: leer cada servicio (`ws` y `duracion`), enviarlo, esperar a recibir el evento de fin (`FINISHED`, `DENIED` o `LEAK_STOP`), **esperar 4 segundos** y enviar el siguiente.</li></ul> |
| **Dockerfiles Lab y Pruebas** | **0 %** | — | `ws/Dockerfile`, `operator/Dockerfile` y generación de `<DNI>SD_Test.log`. |

---

## 5. Seguimiento del Calendario e Hitos del Equipo

```
[✅ COMPLETADO]  7-9 Oct   : Repo GitHub + Contrato completo en /common (Sockets + Topics/Mensajes Kafka)
[✅ COMPLETADO]  10-13 Oct : Sockets, Auth, BD SQLite, Servidor Central, Panel Web y WM_WS_M
[🟡 AL 50%]      14-17 Oct : Flujo de riego con Kafka (Lado Central 100% listo; falta implementar WM_WS_E y WM_FO)
[⏳ EN CURSO]    18-20 Oct : Funcionalidad completa (Fugas en riego, modo fichero en FO)
[⏳ PRÓXIMO]     21-22 Oct : Despliegue Railway + 2 PCs Laboratorio con Docker
[⏳ META]        23 Oct    : Cierre, log <DNI>SD_Test.log, carpeta prompts IA y memoria
```

---

## 6. Hoja de Ruta Inmediata para Julián (Persona B)

1. **Integrar las ramas ahora mismo:**
   * Traer los cambios de `origin/dev` a tu rama `dev-julian` (`git merge origin/dev`) para tener localmente `common/topics.py`, `common/messages.py` y toda la Central lista.
2. **Ajustar 1 línea en [`ws/monitor/WM_WS_M.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/ws/monitor/WM_WS_M.py#L58):**
   * Enviar `f"CHECK_HEALTH#{id_ws}"` para transmitir el identificador de estación al Engine.
3. **Programar `ws/engine/WM_WS_E.py`:**
   * Ya tienes exactamente el formato de mensajes que espera Central (`topics.ORDENES` y `topics.TELEMETRIA`).
4. **Programar `operator/src/WM_FO.py`:**
   * Ya tienes exactamente el formato de peticiones y notificaciones que usa Central (`topics.PETICIONES` y `topics.NOTIF_FO`).
5. **Probar el flujo completo en local** levantando Kafka con el `docker-compose.yml` de Central y ejecutando `WM_Central.py`, `WM_WS_M.py`, `WM_WS_E.py` y `WM_FO.py`.
