# Informe de Estado del Proyecto: Water Management Network
**Asignatura:** Sistemas Distribuidos 2026/2027  
**Fecha de actualización:** Domingo, 18 de octubre de 2026 (19:35h)  
**Fecha objetivo de cierre:** Viernes, 23 de octubre de 2026 (Entrega oficial: semana del 26 de octubre)  
**Equipo:** Persona A (Héctor — Central y Nube) · Persona B (Julián — Estaciones, Operario y Laboratorio)

---

## 1. Resumen Ejecutivo a Fecha de Hoy (18 de Octubre — 19:35h)

En las últimas dos horas has completado y subido a `dev-julian` (`0a8534f..9fa384f`) **todos los módulos de tu parte (Persona B)**:

* **Lo que acabas de dejar 100 % implementado en `dev-julian`:**
  1. **Monitor completo ([`ws/monitor/WM_WS_M.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/ws/monitor/WM_WS_M.py))**: Incluye envío de `CHECK_HEALTH#<id_ws>` cada 1s al Engine, `threading.Lock()` sobre el socket de Central, `PING` periódico cada 5s a Central para mantener la sesión viva, y notificación de `LEAK#<id_ws>` y `RECOVERED#<id_ws>`.
  2. **Engine completo ([`ws/engine/WM_WS_E.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/ws/engine/WM_WS_E.py))**: Conecta con el Monitor, aprende dinámicamente su `id_ws` en el primer `CHECK_HEALTH`, escucha órdenes de Kafka (`START`, `STOP`, `BLOCK` individuales o `ALL`), simula caudal aleatorio (10–14 L/min) emitiendo telemetría cada 1s y soporta control por teclado (`k` avería, `r` recuperar, `s` parada manual).
  3. **Operario de Campo completo ([`operator/src/WM_FO.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/operator/src/WM_FO.py))**: Escucha el catálogo en vivo de estaciones (`wm.fo.stations`) y las notificaciones de su operario (`wm.fo.notifications`). Implementa tanto el **modo manual por menú** como el **modo automático por fichero** ([`operator/servicios_ejemplo.txt`](file:///Users/julianhinojosagil/Documents/Dev/water-management/operator/servicios_ejemplo.txt)) sincronizado con `threading.Event` y la espera obligatoria de **4 segundos** entre servicios.
  4. **Dockerización de Estaciones y Operarios**:
     * [`ws/Dockerfile`](file:///Users/julianhinojosagil/Documents/Dev/water-management/ws/Dockerfile), [`ws/requirements.txt`](file:///Users/julianhinojosagil/Documents/Dev/water-management/ws/requirements.txt) y [`ws/start.sh`](file:///Users/julianhinojosagil/Documents/Dev/water-management/ws/start.sh) (lanza Monitor en segundo plano y Engine en primer plano conectado al teclado interactivo).
     * [`operator/Dockerfile`](file:///Users/julianhinojosagil/Documents/Dev/water-management/operator/Dockerfile), [`operator/requirements.txt`](file:///Users/julianhinojosagil/Documents/Dev/water-management/operator/requirements.txt) y [`operator/start.sh`](file:///Users/julianhinojosagil/Documents/Dev/water-management/operator/start.sh) (soporta tanto modo manual como modo fichero por variables de entorno o argumentos).

* **Con esto, los 4 componentes software del enunciado (`WM_Central`, `WM_WS_M`, `WM_WS_E`, `WM_FO`) y sus Dockerfiles están implementados.**

---

## 2. Auditoría de Ramas Git y Novedades Remotas

| Rama | Último Commit | Estado / Sincronización | Contenido Principal |
| :--- | :--- | :--- | :--- |
| **`origin/dev-julian`** / **`dev-julian`** | `9fa384f` (18 oct, 19:33) | **Sincronizadas y árbol limpio.** Ya incluye el merge `0a8534f` con los commits de Héctor hasta `7586279`. | **Rama más completa del proyecto:** tiene `common/` completo, `central/` completo, `ws/` completo (`WM_WS_M.py`, `WM_WS_E.py`, `Dockerfile`, `start.sh`) y `operator/` completo (`WM_FO.py`, `Dockerfile`, `start.sh`). |
| **`origin/dev-hector`** | `ec2cc93` (18 oct, 19:17) | Tiene **2 commits nuevos** (`69394a8` y `ec2cc93`) respecto a `7586279`. Aún no tiene tus commits de `ws/` ni `operator/`. | Héctor ejecutó `git mv central WM_Central` para renombrar la carpeta `central/` a `WM_Central/` y actualizó la ruta en `WM_Central/docker-compose.yml`. |
| **`origin/dev`** | `085d994` (17 oct) | Desactualizada respecto a `dev-julian` y `dev-hector`. | Falta hacer PR desde `dev-julian` y `dev-hector` hacia `dev`. |
| **`origin/main`** / **`main`** | `e7d3646` (23 sep) | Sincronizadas | Esqueleto inicial intacto. |

---

## 3. Dos Bugs Críticos Detectados en la Revisión de Código (Fáciles de Corregir)

Al auditar línea por línea los nuevos commits en `dev-julian` y `origin/dev-hector`, se han detectado **dos pequeños fallos** que conviene corregir ahora mismo:

### 3.1. Bug en `ws/engine/WM_WS_E.py` (líneas 52 y 64-66): `UnboundLocalError` al pulsar `'s'`
En [`ws/engine/WM_WS_E.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/ws/engine/WM_WS_E.py#L51-L68):
```python
def leer_teclado():
    global averia  # <-- FALTA añadir: , regando
```
* **Qué ocurre:** En la línea 64 haces `if regando:` y en la 66 `regando = False`. Como `regando` se asigna dentro de la función pero en la línea 52 solo pusiste `global averia` (sin `, regando`), Python interpreta `regando` como una variable local de `leer_teclado()`. Si pulsas `'s'` + Enter para detener un riego manualmente, lanza `UnboundLocalError: cannot access local variable 'regando'` y tampoco detiene el bucle `simular_riego`.
* **Solución:** Cambiar la línea 52 a:
  ```python
  global averia, regando
  ```
  *(Y opcionalmente actualizar el `print` de la línea 53 para mencionar también `'s' + Enter para parar riego`).*

### 3.2. Bug en `origin/dev-hector` (commits `69394a8` y `ec2cc93`): `WM_Central/Dockerfile` roto tras renombrar la carpeta
En `origin/dev-hector`, Héctor renombró la carpeta `central/` a `WM_Central/` (`git mv central WM_Central`) y cambió `dockerfile: WM_Central/Dockerfile` en `WM_Central/docker-compose.yml`, pero **dentro de `WM_Central/Dockerfile` quedaron las rutas antiguas**:
```dockerfile
COPY central/requirements.txt .
...
COPY central ./central
...
WORKDIR /app/central
```
* **Qué ocurre:** Al hacer `docker compose build` en `origin/dev-hector`, Docker fallará con `central/requirements.txt: not found`.
* **Solución (cuando integréis `origin/dev-hector`):** Actualizar esas tres líneas en `WM_Central/Dockerfile` para que usen `WM_Central` en lugar de `central`.

---

## 4. Estado Global de Avance por Módulo

| Módulo / Entregable | Responsable | Estado | Detalles |
| :--- | :---: | :---: | :--- |
| **Protocolos Sockets (`/common/protocol`, `/tests`)** | Ambos / Julián | **100 %** | `StandardLRCProtocol`, `LineDelimitedProtocol`, tests y benchmark. |
| **Contrato Kafka (`/common/topics.py`, `messages.py`)** | Ambos / Héctor | **100 %** | 5 topics (`requests`, `notifications`, `stations`, `commands`, `telemetry`) y constructores JSON. |
| **Central (`WM_Central`, SQLite, Panel Web, Docker)** | Persona A (Héctor) | **98 %** | Funcional al 100 % en `dev-julian`; en `origin/dev-hector` solo falta ajustar las rutas internas de `WM_Central/Dockerfile` tras el renombrado de carpeta. |
| **Monitor de Estación ([`ws/monitor/WM_WS_M.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/ws/monitor/WM_WS_M.py))** | Persona B (Julián) | **100 %** | `AUTH`, `PING` cada 5s con `Lock`, `CHECK_HEALTH#<id_ws>` cada 1s, `LEAK` y `RECOVERED`. |
| **Engine de Estación ([`ws/engine/WM_WS_E.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/ws/engine/WM_WS_E.py))** | Persona B (Julián) | **98 %** | Completo (sockets + Kafka + teclado). Solo falta añadir `, regando` en `global averia, regando` (línea 52). |
| **Operario de Campo ([`operator/src/WM_FO.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/operator/src/WM_FO.py))** | Persona B (Julián) | **100 %** | Modo manual interactivo + modo fichero (`servicios_ejemplo.txt`) con espera de 4s entre servicios. |
| **Dockerfiles de WS y FO (`ws/`, `operator/`)** | Persona B (Julián) | **100 %** | `ws/Dockerfile` + `ws/start.sh` y `operator/Dockerfile` + `operator/start.sh`. |
| **Despliegue Cloud (Railway) y Pruebas en 2 PCs Lab** | Ambos | **Pendiente** | Programado para el 21-22 de octubre. |
| **Script / Log `<DNI>SD_Test.log` y Memoria Final** | Ambos | **Pendiente** | Programado para el 22-23 de octubre. |

---

## 5. Seguimiento del Calendario e Hitos del Equipo (a 18 de Octubre — 19:35h)

```
[✅ COMPLETADO]  7-9 Oct   : Repo GitHub + Contrato completo en /common (Sockets + Topics/Mensajes Kafka)
[✅ COMPLETADO]  10-13 Oct : Sockets, Auth, BD SQLite, Servidor Central, Panel Web y WM_WS_M
[✅ COMPLETADO]  14-17 Oct : Flujo de riego con Kafka (Central, Engine y FO implementados)
[🟢 AL 95%]      18-20 Oct : Funcionalidad completa (Fugas, modo fichero FO y Dockerfiles listos; adelantados al calendario)
[⏳ PRÓXIMO]     21-22 Oct : Despliegue en Railway + Pruebas en 2 PCs del Laboratorio
[⏳ META]        23 Oct    : Cierre, log <DNI>SD_Test.log, carpeta prompts IA y memoria
```

---

## 6. Siguientes Pasos Recomendados

1. **Corregir `global averia, regando`** en la línea 52 de [`ws/engine/WM_WS_E.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/ws/engine/WM_WS_E.py#L52).
2. **Probar el sistema completo de extremo a extremo (E2E) en local**:
   * Terminal 1: Levantar Kafka y Central (`docker compose` o `WM_Central.py`).
   * Terminal 2: Lanzar `WM_WS_M.py`.
   * Terminal 3: Lanzar `WM_WS_E.py` (probar riego normal, corte con tecla `k` y recuperación con `r`, y parada manual con `s`).
   * Terminal 4: Lanzar `WM_FO.py` (probar modo manual y modo fichero con `operator/servicios_ejemplo.txt`).
3. **Unificar todo en la rama `dev`** (avisando a Héctor del detalle en `WM_Central/Dockerfile` si vais a mantener el renombrado `central` $\rightarrow$ `WM_Central`).
