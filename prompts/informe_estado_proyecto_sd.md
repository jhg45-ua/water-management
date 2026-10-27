# Informe de Estado del Proyecto: Water Management Network
**Asignatura:** Sistemas Distribuidos 2026/2027  
**Fecha de actualización:** Martes, 27 de octubre de 2026 (22:55h)  
**Fecha de entrega / evaluación:** Viernes, 6 de noviembre de 2026  
**Equipo:** Persona A (Héctor — Central y Nube) · Persona B (Julián — Estaciones, Operario y Laboratorio)

---

## 1. Resumen Ejecutivo a Fecha de Hoy (27 de Octubre — 22:55h)

A última hora de hoy se han completado y dejado preparados en el área de *staging* de `dev-julian` **todos los detalles funcionales y de documentación del repositorio que quedaban pendientes**, dejando el código del sistema al **100 % respecto al enunciado oficial**:

* **Novedades completadas hoy en `dev-julian` (listas en *staging* para hacer `commit`):**
  1. **Cierre al 100 % de [`ws/engine/WM_WS_E.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/ws/engine/WM_WS_E.py) + [`WM_Central/WM_Central.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/WM_Central/WM_Central.py)**:
     * Implementada la opción `'m [seg]'` por teclado en la propia estación para solicitar un **riego manual** a Central (dando de alta automáticamente el identificador `"MANUAL"` en SQLite al iniciar `WM_Central.py`).
     * Actualizado el menú de ayuda en consola (`'k'` avería, `'r'` recuperar, `'m [seg]'` riego manual, `'s'` parar riego).
     * Añadidos los avisos en pantalla cuando Central envía `BLOCK` (*"Estación BLOQUEADA (Fuera de Servicio)"*) y `ACTIVATE` (*"Estación ACTIVADA (Disponible)"*).
  2. **Documentación completa en [`README.md`](file:///Users/julianhinojosagil/Documents/Dev/water-management/README.md) (170 líneas)**:
     * Incluye descripción arquitectónica, argumentos CLI de los 4 ejecutables, detalle del protocolo `<STX><DATA><ETX><LRC>`, guía de despliegue local y guía del escenario distribuido de evaluación (AWS + PC Lab 1 + PC Lab 2).
  3. **Incorporación de [`launch_ws.sh`](file:///Users/julianhinojosagil/Documents/Dev/water-management/launch_ws.sh) al control de versiones**:
     * Script automatizado para lanzar, inspeccionar (`status`) y detener (`stop`) $N$ contenedores de estaciones de riego.
* **Infraestructura Cloud y Laboratorio:**
  * Despliegue en **AWS EC2** operativo con pipeline **CI/CD en GitHub Actions** ([`.github/workflows/ci-cd.yml`](file:///Users/julianhinojosagil/Documents/Dev/water-management/.github/workflows/ci-cd.yml)) y primera prueba básica de ejecución en clase superada.

---

## 2. Auditoría de Ramas Git y Sincronización

| Rama | Último Commit | Estado / Sincronización | Contenido Principal |
| :--- | :--- | :--- | :--- |
| **`dev-julian`** *(rama activa actual)* | `c14638b` + **5 archivos en *staging*** | Sincronizada con `origin/dev-julian` en commits, con **cambios en `git add` sin commitear aún** y **6 commits por detrás de `main`**. *(Existe además `stash@{0}` guardado de cuando se movieron los cambios desde `main`).* | Tiene en *staging* el cierre de `WM_WS_E.py` (riego manual + avisos `BLOCK`/`ACTIVATE`), alta de `"MANUAL"` en `WM_Central.py`, `README.md` completo y `launch_ws.sh`. **Le falta hacer `git merge main`** para incorporar los últimos 6 commits de `main`. |
| **`origin/main`** y **`main`** | `d46597c` (23 oct) | Sincronizadas entre sí. | Producción actual en AWS: tiene `profiles: ["local"]` en `docker-compose.yml` y limpieza de logs en `WM_WS_M.py` y `WM_FO.py`, pero aún no tiene tus mejoras hoy en *staging* de `dev-julian`. |
| **`origin/dev`** y **`dev`** | `22a9f6e` (23 oct) | Sincronizadas entre sí, **5 commits por detrás de `main`**. | Se quedó en el PR #8 previo al paso a `main`. |
| **`origin/dev-hector`** | `22a9f6e` (23 oct) | Igual que `origin/dev` (**5 commits por detrás de `main`**). *(Copia local `dev-hector` en `e7d3646`).* | Igual que `origin/dev`. |

> [!WARNING]
> **Paso crítico de Git ahora mismo en `dev-julian`:**
> Moviste tus cambios desde `main` a `dev-julian` usando `git stash`, pero `dev-julian` aún no tenía integrados los últimos 6 commits de `main` (`d46597c`). Para no perder nada ni pisar el `README.md` de 1 línea que había en `main` (`bf4f120`), sigue este orden exacto:
> 1. `git add prompts/informe_estado_proyecto_sd.md` (para incluir también este informe actualizado en el commit).
> 2. `git commit -m "Completar riego manual en WS, README y script launch_ws"`
> 3. `git merge main` *(te pedirá resolver conflicto en `README.md`: quédate con tu versión nueva de 170 líneas).*
> 4. `git push origin dev-julian` y abrir PR hacia `dev` / `main` (y después puedes borrar el stash antiguo con `git stash drop`).

---

## 3. Estado Global de Avance por Módulo

| Módulo / Entregable | Responsable | Estado | Detalles |
| :--- | :---: | :---: | :--- |
| **Protocolos Sockets (`/common/protocol`, `/tests`)** | Ambos / Julián | **100 %** | `StandardLRCProtocol`, `LineDelimitedProtocol`, tests en CI y benchmark. |
| **Contrato Kafka (`/common/topics.py`, `messages.py`)** | Ambos / Héctor | **100 %** | 5 topics (`requests`, `notifications`, `stations`, `commands`, `telemetry`) y constructores JSON. |
| **Central (`WM_Central`, SQLite, Panel Web, Docker)** | Persona A (Héctor) | **100 %** | Desplegada en AWS EC2 + añadido operario `"MANUAL"` para riegos locales desde estación. |
| **Monitor de Estación ([`ws/monitor/WM_WS_M.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/ws/monitor/WM_WS_M.py))** | Persona B (Julián) | **100 %** | `AUTH`, `PING` silencioso cada 5s con `Lock`, `CHECK_HEALTH#<id_ws>` cada 1s, `LEAK` y `RECOVERED`. |
| **Engine de Estación ([`ws/engine/WM_WS_E.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/ws/engine/WM_WS_E.py))** | Persona B (Julián) | **100 %** | Cerrado al 100 %: telemetría 1s, teclado `k` (fuga), `r` (recuperar), `m [seg]` (riego manual), `s` (parar) y avisos `BLOCK`/`ACTIVATE`. |
| **Operario de Campo ([`operator/src/WM_FO.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/operator/src/WM_FO.py))** | Persona B (Julián) | **100 %** | Modo manual interactivo + modo fichero (`servicios_ejemplo.txt`) con espera de 4s entre servicios. |
| **Dockerfiles y Orquestación (`docker-compose.yml`, `launch_ws.sh`)** | Ambos | **100 %** | Imágenes de los 3 módulos, perfiles Cloud/Local y lanzador `launch_ws.sh`. |
| **Ciclo CI/CD ([`.github/workflows/ci-cd.yml`](file:///Users/julianhinojosagil/Documents/Dev/water-management/.github/workflows/ci-cd.yml))** | Ambos / Julián | **100 %** | GitHub Actions ejecutando tests + `docker build` + despliegue SSH automático a AWS EC2. |
| **Documentación del Repo ([`README.md`](file:///Users/julianhinojosagil/Documents/Dev/water-management/README.md))** | Ambos / Julián | **98 %** | Completado (170 líneas). Solo falta sustituir el DNI placeholder `00000000Y` de Héctor y poner comando Docker en PC LAB 1. |
| **Despliegue AWS y Pruebas en Laboratorio** | Ambos | **85 %** | AWS operativo y prueba básica en clase superada. Falta ensayo final completo (2 FO en PC 1 + 2 WS en PC 2). |
| **Log `<DNI>SD_Test.log`, `/prompts` y Memoria Final** | Ambos | **Pendiente** | Generar `<DNI>SD_Test.log`, recopilar prompts IA y redactar memoria final para UACloud. |

---

## 4. Dos Pequeños Apuntes detectados en el nuevo `README.md`

Al revisar el nuevo [`README.md`](file:///Users/julianhinojosagil/Documents/Dev/water-management/README.md) que tienes en *staging*, está excelente y muy claro; solo tened presentes dos detalles antes de la entrega final:

1. **DNI de Héctor en la cabecera (Línea 7):**
   * Aparece temporalmente como `Héctor García (DNI: 00000000Y)`. Acordaos de poner su DNI real antes de entregar.
2. **Comando con Docker en `PC LAB 1 (Operarios)` (Línea 146):**
   * En la sección de evaluación para `PC LAB 1` aparece `python operator/src/WM_FO.py <IP_AWS>:<PUERTO_KAFKA> OP01`.
   * Como la página 13 del enunciado recalca en negrita que *"El uso de la tecnología Docker para el despliegue es obligatorio en todos los casos para el despliegue de cualquier módulo"*, conviene añadir ahí también el comando equivalente con Docker (`docker run -it --rm -e KAFKA_SERVERS="<HOST_AWS>:9092" -e ID_OPERADOR="OP01" wm-fo`) para usarlo el día de la corrección.

---

## 5. Seguimiento del Calendario e Hitos del Equipo (a 27 de Octubre — 22:55h)

```
[✅ COMPLETADO]  Fase 1 : Repo GitHub + Contrato completo en /common (Sockets + Topics/Mensajes Kafka)
[✅ COMPLETADO]  Fase 2 : Sockets, Auth, BD SQLite, Servidor Central, Panel Web y WM_WS_M
[✅ COMPLETADO]  Fase 3 : Todos los módulos al 100% (Central, Monitor, Engine con riego manual y FO)
[✅ COMPLETADO]  Fase 4 : Pipeline CI/CD + Despliegue en AWS EC2 + README completo + Prueba básica en clase
[🔵 FASE ACTUAL] Cierre : Commit/Merge a main, ensayo completo en 2 PCs Lab, <DNI>SD_Test.log y Memoria
[⏳ ENTREGA]     06 Nov : Entrega final en UACloud y defensa en laboratorio
```

---

## 6. Siguientes Pasos hasta la Entrega Final

1. **Cerrar el commit actual en `dev-julian`, hacer `git merge main` y llevarlo a `dev` y `main`** (con lo que AWS EC2 recibirá automáticamente por CD el alta del operario `"MANUAL"` en `WM_Central.py`).
2. **Realizar el ensayo completo del escenario de evaluación en clase (con Docker en ambos PCs):**
   * AWS EC2 corriendo `kafka` y `central` con `PUBLIC_IP` actualizada.
   * PC Lab 1 ejecutando 2 contenedores de `WM_FO` (`OP01` manual y `OP02` modo fichero).
   * PC Lab 2 ejecutando 2 contenedores de `WM_WS` (`WS-01` y `WS-02`, probando riegos, riego manual `m`, fuga `k`, recuperación `r` y bloqueo desde el Panel Web).
3. **Generar el fichero `<DNI>SD_Test.log` y tomar las capturas de pantalla definitivas.**
4. **Sustituir el DNI de Héctor en `README.md`, recopilar todos los prompts de IA en `/prompts` y subir la Memoria a UACloud.**
