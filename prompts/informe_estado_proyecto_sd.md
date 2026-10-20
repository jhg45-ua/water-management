# Informe de Estado del Proyecto: Water Management Network
**Asignatura:** Sistemas Distribuidos 2026/2027  
**Fecha de actualización:** Domingo, 18 de octubre de 2026 (19:45h)  
**Fecha objetivo de cierre:** Viernes, 23 de octubre de 2026 (Entrega oficial: semana del 26 de octubre)  
**Equipo:** Persona A (Héctor — Central y Nube) · Persona B (Julián — Estaciones, Operario y Laboratorio)

---

## 1. Resumen Ejecutivo a Fecha de Hoy (18 de Octubre — 19:45h)

Con el commit `8eb3c8a` en `dev-julian` (`origin/dev-julian`), **todos los módulos de software de tu parte (Persona B) y del contrato común están al 100 % completados y sin errores conocidos**:

* **Lo que ya está 100 % completado y subido en `dev-julian` (`8eb3c8a`):**
  1. **Módulo compartido (`/common` y `/tests`)**:
     * Protocolos de sockets ([`StandardLRCProtocol`](file:///Users/julianhinojosagil/Documents/Dev/water-management/common/protocol/standard_lrc.py) y [`LineDelimitedProtocol`](file:///Users/julianhinojosagil/Documents/Dev/water-management/common/protocol/line_delim.py)) + tests y benchmarks.
     * Contrato Kafka ([`common/topics.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/common/topics.py) y [`common/messages.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/common/messages.py)).
  2. **Monitor de Estación ([`ws/monitor/WM_WS_M.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/ws/monitor/WM_WS_M.py))**:
     * `AUTH` con Central, `PING` periódico cada 5s con `threading.Lock()`, `CHECK_HEALTH#<id_ws>` cada 1s hacia el Engine, y alertas `LEAK#<id_ws>` / `RECOVERED#<id_ws>`.
  3. **Engine de Estación ([`ws/engine/WM_WS_E.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/ws/engine/WM_WS_E.py))**:
     * Enlace socket con Monitor, asignación dinámica de `id_ws`, consumidor de órdenes Kafka (`START`, `STOP`, `BLOCK` individuales o `ALL`), emisión de telemetría cada 1s y control por teclado (`k` avería, `r` recuperar, `s` parada manual con `global averia, regando` ya corregido en `8eb3c8a`).
  4. **Operario de Campo ([`operator/src/WM_FO.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/operator/src/WM_FO.py))**:
     * Escucha de `wm.fo.stations` y `wm.fo.notifications`, modo manual interactivo y modo automático por fichero ([`operator/servicios_ejemplo.txt`](file:///Users/julianhinojosagil/Documents/Dev/water-management/operator/servicios_ejemplo.txt)) con espera de **4 segundos** entre servicios.
  5. **Dockerfiles de Laboratorio (`ws/` y `operator/`)**:
     * [`ws/Dockerfile`](file:///Users/julianhinojosagil/Documents/Dev/water-management/ws/Dockerfile) + [`ws/start.sh`](file:///Users/julianhinojosagil/Documents/Dev/water-management/ws/start.sh) y [`operator/Dockerfile`](file:///Users/julianhinojosagil/Documents/Dev/water-management/operator/Dockerfile) + [`operator/start.sh`](file:///Users/julianhinojosagil/Documents/Dev/water-management/operator/start.sh).
  6. **Módulo Central (`/central`)**:
     * Integrado en `dev-julian` (versión `7586279` de Héctor, 100 % funcional).

---

## 2. Auditoría de Ramas Git y Sincronización

| Rama | Último Commit | Estado / Sincronización | Contenido Principal |
| :--- | :--- | :--- | :--- |
| **`origin/dev-julian`** / **`dev-julian`** | `8eb3c8a` (18 oct, 19:42) | **Sincronizadas y árbol limpio.** | **Rama con todos los módulos 100 % funcionales:** `common/`, `central/`, `ws/`, `operator/`, `tests/` y `prompts/`. |
| **`origin/dev-hector`** | `ec2cc93` (18 oct, 19:17) | Tiene 2 commits (`69394a8` y `ec2cc93`) donde renombró `central/` a `WM_Central/`. No tiene aún tus módulos `ws/` ni `operator/`. | **Ojo:** En `origin/dev-hector`, dentro de `WM_Central/Dockerfile` siguen puestas las rutas antiguas (`COPY central/...` y `WORKDIR /app/central`), lo cual debe cambiarse a `WM_Central` si se mantiene ese renombrado. |
| **`origin/dev`** | `085d994` (17 oct) | Pendiente de recibir el PR de `dev-julian`. | Versión previa sin `ws/` ni `operator/`. |
| **`origin/main`** / **`main`** | `e7d3646` (23 sep) | Sincronizadas | Esqueleto inicial intacto. |

---

## 3. Estado Global de Avance por Módulo

| Módulo / Entregable | Responsable | Estado | Detalles |
| :--- | :---: | :---: | :--- |
| **Protocolos Sockets (`/common/protocol`, `/tests`)** | Ambos / Julián | **100 %** | `StandardLRCProtocol`, `LineDelimitedProtocol`, tests y benchmark. |
| **Contrato Kafka (`/common/topics.py`, `messages.py`)** | Ambos / Héctor | **100 %** | 5 topics (`requests`, `notifications`, `stations`, `commands`, `telemetry`) y constructores JSON. |
| **Central (`WM_Central`, SQLite, Panel Web, Docker)** | Persona A (Héctor) | **98 %** | Funcional al 100 % en `dev-julian`; en `origin/dev-hector` solo falta ajustar las rutas internas de `WM_Central/Dockerfile` tras el renombrado `central` $\rightarrow$ `WM_Central`. |
| **Monitor de Estación ([`ws/monitor/WM_WS_M.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/ws/monitor/WM_WS_M.py))** | Persona B (Julián) | **100 %** | `AUTH`, `PING` cada 5s con `Lock`, `CHECK_HEALTH#<id_ws>` cada 1s, `LEAK` y `RECOVERED`. |
| **Engine de Estación ([`ws/engine/WM_WS_E.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/ws/engine/WM_WS_E.py))** | Persona B (Julián) | **100 %** | Completo y corregido (`global averia, regando` en commit `8eb3c8a`). |
| **Operario de Campo ([`operator/src/WM_FO.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/operator/src/WM_FO.py))** | Persona B (Julián) | **100 %** | Modo manual interactivo + modo fichero (`servicios_ejemplo.txt`) con espera de 4s entre servicios. |
| **Dockerfiles de WS y FO (`ws/`, `operator/`)** | Persona B (Julián) | **100 %** | `ws/Dockerfile` + `ws/start.sh` y `operator/Dockerfile` + `operator/start.sh`. |
| **Despliegue Cloud (Railway) y Pruebas en 2 PCs Lab** | Ambos | **Pendiente** | Programado para el 21-22 de octubre. |
| **Script / Log `<DNI>SD_Test.log` y Memoria Final** | Ambos | **Pendiente** | Programado para el 22-23 de octubre. |

---

## 4. Seguimiento del Calendario e Hitos del Equipo (a 18 de Octubre — 19:45h)

```
[✅ COMPLETADO]  7-9 Oct   : Repo GitHub + Contrato completo en /common (Sockets + Topics/Mensajes Kafka)
[✅ COMPLETADO]  10-13 Oct : Sockets, Auth, BD SQLite, Servidor Central, Panel Web y WM_WS_M
[✅ COMPLETADO]  14-17 Oct : Flujo de riego con Kafka (Central, Engine y FO implementados)
[✅ COMPLETADO]  18-20 Oct : Funcionalidad completa (Fugas, modo fichero FO y Dockerfiles terminados hoy 18 Oct)
[⏳ PRÓXIMO]     21-22 Oct : Despliegue en Railway + Pruebas en 2 PCs del Laboratorio
[⏳ META]        23 Oct    : Cierre, log <DNI>SD_Test.log, carpeta prompts IA y memoria
```

---

## 5. Siguientes Pasos (Fase de Pruebas e Integración)

1. **Unificar `dev-julian` y `dev-hector` en `dev`:**
   * Antes de mezclar los 2 últimos commits de `origin/dev-hector` (`69394a8` y `ec2cc93`), corregir en `WM_Central/Dockerfile` las rutas `COPY WM_Central/requirements.txt .`, `COPY WM_Central ./WM_Central` y `WORKDIR /app/WM_Central`.
2. **Pruebas End-to-End (E2E) en local:**
   * Levantar Kafka y Central, conectar 2 estaciones (`WS-01`, `WS-02`) y un operario (`OP01`), verificar el Panel Web en `http://localhost:8080`, probar el corte por fuga (`k`) y la ejecución por lote con `servicios_ejemplo.txt`.
3. **Generar el script/log `<DNI>SD_Test.log` y preparar el despliegue en Railway.**
