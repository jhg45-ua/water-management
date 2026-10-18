# Informe de Estado del Proyecto: Water Management Network
**Asignatura:** Sistemas Distribuidos 2026/2027  
**Fecha de actualización:** Domingo, 18 de octubre de 2026 (17:38h)  
**Fecha objetivo de cierre:** Viernes, 23 de octubre de 2026 (Entrega oficial: semana del 26 de octubre)  
**Equipo:** Persona A (Héctor — Central y Nube) · Persona B (Julián — Estaciones, Operario y Laboratorio)

---

## 1. Resumen Ejecutivo a Fecha de Hoy (18 de Octubre — 17:38h)

Hoy domingo 18 de octubre se han producido **10 nuevos commits en `origin/dev-hector` (`ee02aa7..7586279`)** que refinan la Central y añaden mejoras clave para la evaluación y para tu módulo de Operarios (`WM_FO`):

* **Novedades de hoy en `origin/dev-hector` (18 Oct):**
  1. **Nuevo topic Kafka `wm.fo.stations` (`topics.ESTACIONES`) y `messages.msj_estados(estaciones)`**: Central ahora publica cada 1 segundo el listado de todas las estaciones y sus estados. Gracias a esto, tu aplicación de operario (`WM_FO.py`) puede mostrar en todo momento qué estaciones están disponibles (`ACTIVE`) cumpliendo el punto 10 del enunciado sin necesidad de consultar la BD.
  2. **Soporte de `PING` y `REGISTER` en el servidor de sockets de Central (`socket_server.py`)**: Además de `AUTH#id#ubicacion`, `LEAK#id` y `RECOVERED#id`, ahora acepta `PING` (heartbeat del Monitor hacia Central con `TIEMPO_VIDA = 15s`), `REGISTER#id#ubicacion` y `AUTH#id`.
  3. **Volumen total histórico por estación (`db.py`, `state.py`, `index.html`)**: Se guarda en SQLite (`columna total`) y se muestra en el panel web el acumulado histórico de litros suministrados por cada estación, además de actualizar las etiquetas del panel web al inglés (`Available`, `Watering`, `Leak (Averiada)`, `Out of Service`, `Disconnected`).
  4. **Versión fijada `kafka-python==2.2.15` en `requirements.txt`**: Garantiza compatibilidad con Python 3.12/3.13/3.14.

* **Estado global del proyecto:**
  * **Persona A (Héctor — Central, BD, Panel, Contrato Kafka)**: **100 % completado** (en `origin/dev-hector`).
  * **Persona B (Julián — Estaciones, Operario, Laboratorio)**:
    * Protocolos de sockets (`/common/protocol/` y `/tests/`): **100 % completado**.
    * Monitor (`ws/monitor/WM_WS_M.py`): **95 % completado** (en `dev-julian`).
    * Engine (`ws/engine/WM_WS_E.py`): **0 % (Pendiente)**.
    * Field Operator (`operator/src/WM_FO.py`): **0 % (Pendiente)**.
    * Dockerfiles de `ws` y `operator` + script de log `<DNI>SD_Test.log`: **0 % (Pendiente)**.

---

## 2. Auditoría de Ramas Git y Sincronización

| Rama | Último Commit | Estado / Sincronización | Contenido Principal |
| :--- | :--- | :--- | :--- |
| **`origin/main`** / **`main`** | `e7d3646` (23 sep) | Sincronizadas | Esqueleto inicial intacto. |
| **`origin/dev-hector`** | `7586279` (18 oct, 17:12) | **Rama más adelantada de Central** (10 commits por delante de `origin/dev` y 28 por delante de `dev-julian`). | Contiene toda la Central v2: nuevo topic `ESTACIONES`, `PING`/`REGISTER` en sockets, total histórico de litros en SQLite/Panel y `kafka-python==2.2.15`. *(Aún no volcado a `origin/dev` ni tiene tu `WM_WS_M.py`).* |
| **`origin/dev`** | `085d994` (17 oct) | 10 commits por detrás de `origin/dev-hector`. | Versión de ayer de Central + Kafka + Panel + Docker. |
| **`origin/dev-julian`** / **`dev-julian`** | `02d9bb0` (16 oct) | Sincronizadas entre sí y árbol limpio, pero **les faltan los 28 commits de Héctor (`origin/dev-hector`)**. | Contiene `common/protocol/`, `tests/`, [`ws/monitor/WM_WS_M.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/ws/monitor/WM_WS_M.py) y [`prompts/informe_estado_proyecto_sd.md`](file:///Users/julianhinojosagil/Documents/Dev/water-management/prompts/informe_estado_proyecto_sd.md). |

> [!IMPORTANT]
> **Sincronización recomendada antes de programar `WM_WS_E` y `WM_FO`:**
> Como los últimos cambios de Héctor (incluido el nuevo topic `ESTACIONES` en `common/topics.py` y `msj_estados` en `common/messages.py`) están en `origin/dev-hector`, conviene hacer `git merge origin/dev-hector` en tu rama `dev-julian` (o que Héctor haga merge de `dev-hector` a `dev` y tú hagas merge de `origin/dev`). No hay ningún conflicto de archivos.

---

## 3. Contrato Completo de Comunicaciones (Sockets + Kafka)

### 3.1. Comandos por Sockets (`WM_WS_M` $\leftrightarrow$ `WM_Central` y `WM_WS_M` $\leftrightarrow$ `WM_WS_E`)

| Enlace | Emisor $\rightarrow$ Receptor | Mensaje | Respuesta | Descripción |
| :--- | :--- | :--- | :--- | :--- |
| **Monitor $\rightarrow$ Central** | `WM_WS_M` $\rightarrow$ `WM_Central` | `REGISTER#<id>#<ubicacion>` | `OK` / `KO#...` | Da de alta la estación en la BD (opcional si se usa `AUTH` con 3 campos). |
| **Monitor $\rightarrow$ Central** | `WM_WS_M` $\rightarrow$ `WM_Central` | `AUTH#<id>#<ubicacion>` o `AUTH#<id>` | `OK` / `KO#...` | Autentica la estación y la pasa a estado `ACTIVE`. |
| **Monitor $\rightarrow$ Central** | `WM_WS_M` $\rightarrow$ `WM_Central` | `PING` | `OK` | Mantiene viva la conexión (Central tiene `TIEMPO_VIDA = 15s`). |
| **Monitor $\rightarrow$ Central** | `WM_WS_M` $\rightarrow$ `WM_Central` | `LEAK#<id>` | `OK` / `KO#...` | Pone la estación en `LEAK` (rojo) y si estaba regando corta el riego por Kafka. |
| **Monitor $\rightarrow$ Central** | `WM_WS_M` $\rightarrow$ `WM_Central` | `RECOVERED#<id>` | `OK` / `KO#...` | Si estaba en `LEAK`, la devuelve a `ACTIVE` (verde). |
| **Monitor $\rightarrow$ Engine** | `WM_WS_M` $\rightarrow$ `WM_WS_E` | `CHECK_HEALTH` *(rec.: `CHECK_HEALTH#<id>`)* | `OK` / `KO` | Comprobación de salud cada 1 segundo. |

> [!WARNING]
> **Detalle crítico en `socket_server.py` (commit `73b0b1f` de `origin/dev-hector`) y `WM_WS_M.py`:**
> Héctor ha añadido `TIEMPO_VIDA = 15` segundos en `socket_server.py`. Además, como `sock_central` en [`WM_WS_M.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/ws/monitor/WM_WS_M.py) se quedaba en un `while True: time.sleep(1)` sin enviar nada si no había fugas, es muy buena práctica que en el bucle principal de `WM_WS_M.py` envíes un `protocol.send_request(sock_central, "PING")` cada ~5 segundos (protegiendo el uso de `sock_central` con un `threading.Lock()` para que el hilo `vigilar_engine` y el hilo principal no escriban a la vez en `sock_central`).

---

### 3.2. Topics y Mensajes JSON de Kafka (`common/topics.py` y `common/messages.py`)

#### Topics definidos:
* `topics.PETICIONES = "wm.fo.requests"` — Operario (`WM_FO`) $\rightarrow$ Central.
* `topics.NOTIF_FO = "wm.fo.notifications"` — Central $\rightarrow$ Operario (`WM_FO`).
* `topics.ESTACIONES = "wm.fo.stations"` — Central $\rightarrow$ Operario (`WM_FO`) *(Nuevo hoy: estado de todas las WS cada 1s)*.
* `topics.ORDENES = "wm.ws.commands"` — Central $\rightarrow$ Engine (`WM_WS_E`).
* `topics.TELEMETRIA = "wm.ws.telemetry"` — Engine (`WM_WS_E`) $\rightarrow$ Central.

#### Constructores JSON en `common/messages.py`:

| Dirección | Función en `messages.py` | Payload JSON |
| :--- | :--- | :--- |
| **FO $\rightarrow$ Central** | `msj_pet(operario, ws, duracion)` | `{"type": "REQUEST", "operator": "OP01", "ws": "WS01", "duration": 30}` |
| **Central $\rightarrow$ FO** | `msj_notif(operario, ws, evento, texto, caudal, volumen)` | `{"type": "NOTIFY", "operator": "OP01", "ws": "WS01", "event": "RECEIVED\|AUTHORIZED\|DENIED\|PROGRESS\|FINISHED\|LEAK_STOP", "text": "...", "flow": 10, "volume": 50}` |
| **Central $\rightarrow$ FO** | `msj_estados(estaciones)` *(Nuevo)* | `{"type": "STATIONS", "stations": {"WS01": {"location": "...", "status": "ACTIVE"}}}` |
| **Central $\rightarrow$ Engine** | `msj_orden(ws, accion, operario, duracion)` | `{"type": "COMMAND", "ws": "WS01\|ALL", "action": "START\|STOP\|BLOCK\|ACTIVATE", "operator": "OP01", "duration": 30}` |
| **Engine $\rightarrow$ Central** | `msj_telem(ws, operario, caudal, volumen, final)` | `{"type": "TELEMETRY", "ws": "WS01", "operator": "OP01", "flow": 12.5, "volume": 25.0, "final": false\|true}` |

---

## 4. Estado Detallado de tus Módulos (Persona B — Julián)

| Módulo / Archivo | Estado | Lo que ya está hecho | Lo que falta por implementar |
| :--- | :---: | :--- | :--- |
| **Monitor (`WM_WS_M`)**<br>[`ws/monitor/WM_WS_M.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/ws/monitor/WM_WS_M.py) | **95 %** | <ul><li>Conexión y `AUTH#id#ubicacion` con Central.</li><li>Servidor local para el Engine y bucle `vigilar_engine` cada 1s.</li><li>Envío de `LEAK#<id_ws>` y `RECOVERED#<id_ws>`.</li></ul> | <ul><li>Enviar `f"CHECK_HEALTH#{id_ws}"` al Engine para pasarle su `id_ws`.</li><li>Añadir un `threading.Lock()` para `sock_central` y enviar `PING` periódico a Central en el bucle principal para mantener viva la sesión frente a `TIEMPO_VIDA`.</li></ul> |
| **Engine (`WM_WS_E`)**<br>`ws/engine/WM_WS_E.py` | **0 %**<br>*(Prioridad 1)* | Solo existe `ws/engine/.gitkeep`. | <ul><li>Argumentos CLI: `<ip_kafka:puerto_kafka> <ip_monitor:puerto_monitor> [protocolo]`.</li><li>Conectar por socket al Monitor (`init_connection`), recibir `CHECK_HEALTH#<id_ws>` cada 1s y responder `"OK"` o `"KO"`.</li><li>Escuchar `topics.ORDENES` (`"wm.ws.commands"`): procesar `START`, `STOP`, `BLOCK`, `ACTIVATE` para su `id_ws` o `"ALL"`.</li><li>Simulación de riego: enviar cada **1 segundo** `msj_telem(id_ws, operario, caudal, volumen, final=False)` a `topics.TELEMETRIA` y al terminar el tiempo o parar manualmente enviar `final=True`.</li><li>Menú/teclado interactivo en tiempo de ejecución: simular avería (`KO`), recuperar avería (`OK`), iniciar riego manual o detener riego en curso.</li></ul> |
| **Field Operator (`WM_FO`)**<br>`operator/src/WM_FO.py` | **0 %**<br>*(Prioridad 2)* | Solo existe `operator/src/.gitkeep`. | <ul><li>Argumentos CLI: `<ip_kafka:puerto_kafka> <id_operador> [fichero_servicios]`.</li><li>Escuchar `topics.ESTACIONES` (`"wm.fo.stations"`) para guardar y mostrar al operario las estaciones disponibles (`ACTIVE`).</li><li>Escuchar `topics.NOTIF_FO` (`"wm.fo.notifications"`) filtrando `msg["operator"] == id_operador` e imprimir cada paso (`RECEIVED`, `AUTHORIZED`, `DENIED`, `PROGRESS`, `FINISHED`, `LEAK_STOP`).</li><li>Modo manual por consola y modo automático por **fichero** (enviar servicio $\rightarrow$ esperar conclusión $\rightarrow$ **esperar 4 segundos** $\rightarrow$ siguiente servicio).</li></ul> |
| **Dockerfiles Lab y Pruebas** | **0 %**<br>*(Prioridad 3)* | — | `ws/Dockerfile`, `operator/Dockerfile` y script de pruebas con generación de `<DNI>SD_Test.log`. |

---

## 5. Seguimiento del Calendario e Hitos del Equipo (a 18 de Octubre)

```
[✅ COMPLETADO]  7-9 Oct   : Repo GitHub + Contrato completo en /common (Sockets + Topics/Mensajes Kafka)
[✅ COMPLETADO]  10-13 Oct : Sockets, Auth, BD SQLite, Servidor Central, Panel Web y WM_WS_M
[🟡 AL 55%]      14-17 Oct : Flujo de riego con Kafka (Central al 100%; falta programar WM_WS_E y WM_FO)
[🔴 EN CURSO]    18-20 Oct : Funcionalidad completa (HOY es 18 Oct: toca cerrar WM_WS_E y WM_FO)
[⏳ PRÓXIMO]     21-22 Oct : Despliegue Railway + 2 PCs Laboratorio con Docker
[⏳ META]        23 Oct    : Cierre, log <DNI>SD_Test.log, carpeta prompts IA y memoria
```

---

## 6. Plan de Acción Inmediato para Hoy (18 de Octubre)

1. **Sincronizar tu rama `dev-julian` con `origin/dev-hector`** (`git merge origin/dev-hector`) para traerte toda la Central terminada, el `docker-compose.yml` con Kafka y los archivos `common/topics.py` y `common/messages.py`.
2. **Actualizar [`ws/monitor/WM_WS_M.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/ws/monitor/WM_WS_M.py)** (añadir el `id_ws` en `CHECK_HEALTH#<id_ws>` y el `PING` a Central con `Lock`).
3. **Implementar `ws/engine/WM_WS_E.py`**.
4. **Implementar `operator/src/WM_FO.py`**.
5. **Probar todo el circuito en local** con el contenedor de Kafka de `central/docker-compose.yml`.
