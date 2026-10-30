# Informe de Estado del Proyecto: Water Management Network
**Asignatura:** Sistemas Distribuidos 2026/2027  
**Fecha de actualización:** Viernes, 30 de octubre de 2026 (09:50h)  
**Fecha de entrega / evaluación:** Viernes, 6 de noviembre de 2026  
**Equipo:** Persona A (Héctor — Central y Nube) · Persona B (Julián — Estaciones, Operario y Laboratorio)

---

## 1. Resumen Ejecutivo a Fecha de Hoy (30 de Octubre — 09:50h)

A una semana exacta de la entrega final (6 de noviembre), el código en producción (`main` en `731c8d5`) ya integra el **100 % de la funcionalidad obligatoria y la documentación completa**, y en el directorio de trabajo local de `dev-julian` tenéis preparadas **mejoras adicionales de robustez y concurrencia** listas para commitear:

* **Ya integrado y desplegado en `main` (`731c8d5`, noche del 27 oct):**
  1. **Cierre de [`ws/engine/WM_WS_E.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/ws/engine/WM_WS_E.py) y [`WM_Central/WM_Central.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/WM_Central/WM_Central.py)**: Riego manual `'m [seg]'` desde estación (operario `"MANUAL"` pre-registrado en SQLite) y avisos por consola de `BLOCK`/`ACTIVATE`.
  2. **[`README.md`](file:///Users/julianhinojosagil/Documents/Dev/water-management/README.md) definitivo (199 líneas)**: Con los DNIs reales de ambos autores (`48795869N` y `48770607G`) y todos los comandos de laboratorio (`PC LAB 1` y `PC LAB 2`) usando **Docker** obligatorio.
  3. **Scripts de evaluación listos**: [`launch_ws.sh`](file:///Users/julianhinojosagil/Documents/Dev/water-management/launch_ws.sh) parametrizado para AWS (`CENTRAL_ADDR`, `KAFKA_SERVERS`) y lote de pruebas [`operator/servicios_evaluacion.txt`](file:///Users/julianhinojosagil/Documents/Dev/water-management/operator/servicios_evaluacion.txt).
* **Nuevas mejoras de robustez en local (`dev-julian`, sin commitear aún — 9 archivos modificados + `.env.example`):**
  1. **Sincronización y *timeout* en [`operator/src/WM_FO.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/operator/src/WM_FO.py)**: Espera activa a que Kafka asigne particiones (`consumidor.assignment()`) antes de lanzar la primera petición en modo fichero (`consumidor_listo`) y *timeout* de seguridad (`duracion + 30` s) en `evento_fin_riego.wait()`.
  2. **Reintentos de conexión por socket y validación estricta de protocolo**: Bucles de reconexión inicial en [`ws/monitor/WM_WS_M.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/ws/monitor/WM_WS_M.py) (hacia Central en AWS) y [`ws/engine/WM_WS_E.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/ws/engine/WM_WS_E.py) (hacia Monitor), validación explícita de `'lrc'`/`'line'` en los 3 módulos de sockets y soporte de `ENV PROTO=lrc` en [`WM_Central/Dockerfile`](file:///Users/julianhinojosagil/Documents/Dev/water-management/WM_Central/Dockerfile).
  3. **Transiciones de estado atómicas en Central**: Uso de `state.cambiar_si(...)` tanto en `AUTH` ([`WM_Central/src/socket_server.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/WM_Central/src/socket_server.py), evitando condiciones de carrera con Monitores duplicados) como en `estacion_con_fuga` ([`WM_Central/src/kafka_handlers.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/WM_Central/src/kafka_handlers.py), evitando pisar el estado `OUT_OF_SERVICE`).
  4. **Inyección de `PUBLIC_IP` en CI/CD y plantilla [`.env.example`](file:///Users/julianhinojosagil/Documents/Dev/water-management/.env.example)**: Actualización de [`.github/workflows/ci-cd.yml`](file:///Users/julianhinojosagil/Documents/Dev/water-management/.github/workflows/ci-cd.yml) para exportar `PUBLIC_IP=$AWS_HOST` al desplegar en EC2.

---

## 2. Auditoría de Ramas Git y Sincronización

| Rama | Último Commit | Estado / Sincronización | Contenido Principal |
| :--- | :--- | :--- | :--- |
| **`dev-julian`** *(rama activa actual)* | `3c1def0` (27 oct) + **9 modificados y 1 sin seguimiento** | Sincronizada con `origin/dev-julian` en commits, pero **6 commits por detrás de `main`** y con cambios locales sin `git add`/`commit`. *(Sigue existiendo `stash@{0}` antiguo del 27 oct).* | Contiene en el árbol de trabajo las mejoras de robustez del 28–30 oct (`WM_FO.py`, reintentos socket en `WS`, transiciones atómicas en `WM_Central`, `PROTO` en Dockerfile, `.env.example` y `ci-cd.yml`). |
| **`origin/main`** y **`main`** | `731c8d5` (27 oct, 23:44h) | Sincronizadas entre sí. **Rama más adelantada en commits.** | Producción actual en AWS: integra el cierre de `WM_WS_E.py`, `README.md` completo (con ambos DNIs y Docker), `launch_ws.sh`, `servicios_evaluacion.txt` y `profiles: ["local"]`. Aún no tiene los 10 cambios locales de `dev-julian`. |
| **`origin/dev`** y **`dev`** | `40554c8` (27 oct, 23:43h) | Sincronizadas entre sí, **5 commits por detrás de `main`**. | Tiene el merge de `3c1def0`, pero nunca recibió de vuelta los commits directos previos de `main` (`d46597c`) ni el merge `731c8d5`. |
| **`origin/dev-hector`** | `d46597c` (23 oct) | Actualizada en remoto respecto a la revisión anterior (`22a9f6e` → `d46597c`), **3 commits por detrás de `main`**. *(Copia local `dev-hector` obsoleta en `e7d3646`).* | Igual que `main` antes del merge `731c8d5` del 27 oct (le falta el nuevo `README.md`, `launch_ws.sh` y cierre de `WM_WS_E.py`). |

> [!WARNING]
> **Atención al sincronizar `dev-julian` con `main` (evitar regresiones de consola):**
> Como `dev-julian` (`3c1def0`) no llegó a hacer `git merge main` (`731c8d5`) antes de empezar los retoques del 28–30 de octubre, al fusionar con `main` aparecerán conflictos en [`docker-compose.yml`](file:///Users/julianhinojosagil/Documents/Dev/water-management/docker-compose.yml), [`ws/monitor/WM_WS_M.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/ws/monitor/WM_WS_M.py) y [`operator/src/WM_FO.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/operator/src/WM_FO.py):
> 1. Antes de commitear en `dev-julian`, revisa la línea 132 de [`ws/monitor/WM_WS_M.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/ws/monitor/WM_WS_M.py#L132): en `dev-julian` sigue activo `print(f"[{id_ws}] Ping enviado a Central (sesión viva)")` cada 5 s, mientras que en `main` lo habíais comentado (`# print(...)`) para no ensuciar la terminal al hacer `docker attach ws-01`.
> 2. Haz `git add . && git commit -m "Mejoras de robustez en Kafka/Sockets, estados atómicos y CI/CD"` en `dev-julian`.
> 3. Ejecuta `git merge main` y resuelve quedándote con tu versión nueva en los 3 ficheros, sube a `dev` y `main`, e igualad todas las ramas (`dev`, `dev-julian`, `dev-hector`) con `main`. *(El antiguo `stash@{0}` ya está incluido en `main`, así que puedes borrarlo con `git stash drop`).*

---

## 3. Estado Global de Avance por Módulo

| Módulo / Entregable | Responsable | Estado | Detalles |
| :--- | :---: | :---: | :--- |
| **Protocolos Sockets (`/common/protocol`, `/tests`)** | Ambos / Julián | **100 %** | `StandardLRCProtocol`, `LineDelimitedProtocol`, tests unitarios superados (`lrc` y `line`) y benchmark. |
| **Contrato Kafka (`/common/topics.py`, `messages.py`)** | Ambos / Héctor | **100 %** | 5 topics (`requests`, `notifications`, `stations`, `commands`, `telemetry`) y constructores JSON. |
| **Central (`WM_Central`, SQLite, Panel Web, Docker)** | Persona A (Héctor) | **100 %** | Desplegada en AWS EC2 + operario `"MANUAL"` + transiciones atómicas `cambiar_si` en `AUTH` y `LEAK` + `ENV PROTO` en Docker. |
| **Monitor de Estación ([`ws/monitor/WM_WS_M.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/ws/monitor/WM_WS_M.py))** | Persona B (Julián) | **100 %** | Reconexión inicial automática a Central, `AUTH`, `PING` cada 5s con `Lock`, `CHECK_HEALTH` cada 1s (capturando también `ValueError` de LRC), `LEAK` y `RECOVERED`. |
| **Engine de Estación ([`ws/engine/WM_WS_E.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/ws/engine/WM_WS_E.py))** | Persona B (Julián) | **100 %** | Reconexión inicial automática al Monitor, telemetría 1s, teclado `k`, `r`, `m [seg]`, `s` y avisos `BLOCK`/`ACTIVATE`. |
| **Operario de Campo ([`operator/src/WM_FO.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/operator/src/WM_FO.py))** | Persona B (Julián) | **100 %** | Modo manual + modo fichero (`servicios_evaluacion.txt`) con espera de asignación de particiones Kafka (`consumidor_listo`), pausa de 4s y *timeout* de seguridad. |
| **Dockerfiles y Orquestación (`docker-compose.yml`, `launch_ws.sh`)** | Ambos | **100 %** | Imágenes de los 3 módulos, perfiles Cloud/Local, `.env.example` y lanzador `launch_ws.sh` parametrizado para AWS. |
| **Ciclo CI/CD ([`.github/workflows/ci-cd.yml`](file:///Users/julianhinojosagil/Documents/Dev/water-management/.github/workflows/ci-cd.yml))** | Ambos / Julián | **100 %** | GitHub Actions ejecutando compilación, tests LRC/Line, builds Docker y despliegue SSH en AWS EC2 con `PUBLIC_IP`. |
| **Documentación del Repo ([`README.md`](file:///Users/julianhinojosagil/Documents/Dev/water-management/README.md))** | Ambos / Julián | **100 %** | Cerrado al 100 % (corregidos los DNIs reales de ambos autores y comandos con Docker en `PC LAB 1` y `PC LAB 2`). |
| **Despliegue AWS y Pruebas en Laboratorio** | Ambos | **85 %** | AWS operativo y prueba básica en clase superada. Falta ensayo final completo con los últimos parches de robustez. |
| **Log `<DNI>SD_Test.log`, `/prompts` y Memoria Final** | Ambos | **Pendiente** | Generar `<DNI>SD_Test.log`, añadir historial de prompts de IA en `/prompts` y redactar memoria final para UACloud. |

---

## 4. Observaciones Técnicas Aplicadas en la Revisión

Los cambios locales en `dev-julian` pasan limpiamente `compileall` y los tests de ambos protocolos (`StandardLRCProtocol` y `LineDelimitedProtocol`). Se han corregido y dejado aplicados los **dos matices técnicos** identificados:

1. **Actualización de `.env` cuando cambia la IP de AWS Learner Lab ([`.github/workflows/ci-cd.yml`](file:///Users/julianhinojosagil/Documents/Dev/water-management/.github/workflows/ci-cd.yml#L67-L76)):**
   * Ajustado el bloque SSH para sobrescribir siempre el fichero `.env` con las comillas escapadas (`echo \"PUBLIC_IP=$AWS_HOST\" > .env`), garantizando que cada vez que se reinicie la sesión en AWS Learner Lab la nueva IP pública quede correctamente persistida en la instancia EC2.
2. **Silenciado del `PING` cada 5 s en [`ws/monitor/WM_WS_M.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/ws/monitor/WM_WS_M.py#L132):**
   * Comentado el `print` del Ping para no ensuciar la salida estándar compartida entre Monitor y Engine en el contenedor Docker al interactuar por teclado (`docker attach ws-01`).

---

## 5. Seguimiento del Calendario e Hitos del Equipo (a 30 de Octubre — 09:50h)

```
[✅ COMPLETADO]  Fase 1 : Repo GitHub + Contrato completo en /common (Sockets + Topics/Mensajes Kafka)
[✅ COMPLETADO]  Fase 2 : Sockets, Auth, BD SQLite, Servidor Central, Panel Web y WM_WS_M
[✅ COMPLETADO]  Fase 3 : Todos los módulos al 100% (Central, Monitor, Engine y FO) + Blindaje concurrencia
[✅ COMPLETADO]  Fase 4 : Pipeline CI/CD + Despliegue en AWS EC2 + README 100% + Prueba básica en clase
[🔵 FASE ACTUAL] Cierre : Subir mejoras locales a main, ensayo completo Lab, <DNI>SD_Test.log, /prompts y Memoria
[⏳ ENTREGA]     06 Nov : Entrega final en UACloud y defensa en laboratorio (quedan 7 días)
```

---

## 6. Siguientes Pasos hasta la Entrega Final (6 de Noviembre)

1. **Commitear los cambios en `dev-julian`, fusionar con `main` e igualar ramas (`dev`, `dev-julian`, `dev-hector` y `main`).**
2. **Ejecutar el ensayo completo del escenario de evaluación (con Docker en ambos PCs contra AWS):**
   * Verificar `AWS_HOST` actualizado en GitHub Secrets al arrancar AWS Learner Lab.
   * **PC Lab 1:** Lanzar 2 contenedores `wm-fo` (`OP01` interactivo y `OP02` con `operator/servicios_evaluacion.txt`).
   * **PC Lab 2:** Lanzar al menos 2 contenedores de estaciones con `CENTRAL_ADDR="<HOST_AWS>:5000" KAFKA_SERVERS="<HOST_AWS>:9092" ./launch_ws.sh 2`, probando riegos simultáneos, riego manual `'m'`, avería `'k'`, recuperación `'r'` y órdenes `ALL`/individuales desde el Panel Web.
3. **Generar y commitear el log de pruebas `<DNI>SD_Test.log` y añadir en `/prompts` todos los prompts de IA utilizados por ambos integrantes.**
4. **Dar acceso al profesor en el repositorio GitHub, cerrar las capturas de pantalla y subir la Memoria Final en PDF a UACloud.**
