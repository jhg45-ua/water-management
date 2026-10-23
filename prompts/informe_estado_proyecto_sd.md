# Informe de Estado del Proyecto: Water Management Network
**Asignatura:** Sistemas Distribuidos 2026/2027  
**Fecha de actualización:** Martes, 20 de octubre de 2026 (10:06h)  
**Fecha objetivo de cierre:** Viernes, 23 de octubre de 2026 (Entrega oficial: semana del 26 de octubre)  
**Equipo:** Persona A (Héctor — Central y Nube) · Persona B (Julián — Estaciones, Operario y Laboratorio)

---

## 1. Resumen Ejecutivo a Fecha de Hoy (20 de Octubre — 10:06h)

Con los merges completados en las ramas `dev` (`2f35619`) y `dev-julian` (`b192d19`), **el 100 % del desarrollo de software y la configuración de contenedores Docker de ambos miembros del equipo ya está unificado, integrado y con todos los bugs previos corregidos**:

* **Lo que ya está 100 % completado e integrado en `dev` y `dev-julian`:**
  1. **Módulo compartido (`/common` y `/tests`)**:
     * Protocolos de sockets ([`StandardLRCProtocol`](file:///Users/julianhinojosagil/Documents/Dev/water-management/common/protocol/standard_lrc.py) y [`LineDelimitedProtocol`](file:///Users/julianhinojosagil/Documents/Dev/water-management/common/protocol/line_delim.py)) + tests y benchmarks.
     * Contrato Kafka ([`common/topics.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/common/topics.py) y [`common/messages.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/common/messages.py)).
  2. **Sistema Central (`/WM_Central`)**:
     * Persistencia SQLite con acumulado de litros por estación (`db.py`), estado en memoria *thread-safe* (`state.py`), servidor de sockets con `ESPERA_VIDA=15s` (`socket_server.py`), manejadores Kafka con difusión de estaciones cada 1s (`kafka_handlers.py`), menú por consola (`commands.py`), panel web Flask en puerto 8080 (`panel/`) e imagen Docker con rutas ya corregidas (`Dockerfile`).
     * Orquestación local: [`docker-compose.yml`](file:///Users/julianhinojosagil/Documents/Dev/water-management/docker-compose.yml) en la raíz para levantar Kafka 3.8.1 (KRaft) + `WM_Central`.
  3. **Monitor de Estación ([`ws/monitor/WM_WS_M.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/ws/monitor/WM_WS_M.py))**:
     * `AUTH` con Central, `PING` periódico cada 5s con `threading.Lock()`, `CHECK_HEALTH#<id_ws>` cada 1s hacia el Engine, y alertas `LEAK#<id_ws>` / `RECOVERED#<id_ws>`.
  4. **Engine de Estación ([`ws/engine/WM_WS_E.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/ws/engine/WM_WS_E.py))**:
     * Enlace socket con Monitor, asignación dinámica de `id_ws`, consumidor de órdenes Kafka (`START`, `STOP`, `BLOCK` individuales o `ALL`), emisión de telemetría cada 1s y control por teclado (`k` avería, `r` recuperar, `s` parada manual con `global averia, regando` ya corregido).
  5. **Operario de Campo ([`operator/src/WM_FO.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/operator/src/WM_FO.py))**:
     * Escucha de `wm.fo.stations` y `wm.fo.notifications`, modo manual interactivo y modo automático por fichero ([`operator/servicios_ejemplo.txt`](file:///Users/julianhinojosagil/Documents/Dev/water-management/operator/servicios_ejemplo.txt)) con espera de **4 segundos** entre servicios.
  6. **Dockerfiles de Laboratorio (`ws/` y `operator/`)**:
     * [`ws/Dockerfile`](file:///Users/julianhinojosagil/Documents/Dev/water-management/ws/Dockerfile) + [`ws/start.sh`](file:///Users/julianhinojosagil/Documents/Dev/water-management/ws/start.sh) y [`operator/Dockerfile`](file:///Users/julianhinojosagil/Documents/Dev/water-management/operator/Dockerfile) + [`operator/start.sh`](file:///Users/julianhinojosagil/Documents/Dev/water-management/operator/start.sh).

> [!NOTE]
> **Infraestructura Cloud:** La plataforma definitiva para alojar la Central (`WM_Central`), la base de datos (`SQLite`) y el clúster de `Kafka` se encuentra actualmente **pendiente de selección entre Railway y AWS (AWS Learner Lab)**, tal y como permite el enunciado.

---

## 2. Auditoría de Ramas Git y Sincronización

| Rama | Último Commit | Estado / Sincronización | Contenido Principal |
| :--- | :--- | :--- | :--- |
| **`origin/dev`** y **`dev`** | `2f35619` (19 oct) | **100 % sincronizadas** entre local y remoto. | **Rama común integrada:** contiene `common/`, `WM_Central/`, `ws/`, `operator/`, `tests/`, `prompts/` y `docker-compose.yml` en la raíz. |
| **`origin/dev-julian`** y **`dev-julian`** | `b192d19` (19 oct) | **100 % sincronizadas** con `dev` (`git diff` vacío respecto a `origin/dev`). | Idéntica a `origin/dev` tras el merge del PR #7. Árbol de trabajo limpio. |
| **`origin/dev-hector`** | `0a902d1` (19 oct) | Sus cambios ya están dentro de `dev`, pero le falta hacer `git merge origin/dev` para tener `ws/` y `operator/`. | Héctor debe actualizar su rama desde `dev` o trabajar ya directamente en `dev`. |
| **`origin/main`** y **`main`** | `e7d3646` (23 sep) | Sincronizadas entre sí. | Esqueleto inicial intacto, lista para recibir el merge final de entrega y activar el autodespliegue CD hacia la plataforma Cloud elegida. |

---

## 3. Estado Global de Avance por Módulo

| Módulo / Entregable | Responsable | Estado | Detalles |
| :--- | :---: | :---: | :--- |
| **Protocolos Sockets (`/common/protocol`, `/tests`)** | Ambos / Julián | **100 %** | `StandardLRCProtocol`, `LineDelimitedProtocol`, tests y benchmark. |
| **Contrato Kafka (`/common/topics.py`, `messages.py`)** | Ambos / Héctor | **100 %** | 5 topics (`requests`, `notifications`, `stations`, `commands`, `telemetry`) y constructores JSON. |
| **Central (`WM_Central`, SQLite, Panel Web, Docker)** | Persona A (Héctor) | **100 %** | SQLite con histórico total, estado en memoria, servidor sockets con timeout 15s, manejadores Kafka, Panel Web y Docker. |
| **Monitor de Estación ([`ws/monitor/WM_WS_M.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/ws/monitor/WM_WS_M.py))** | Persona B (Julián) | **100 %** | `AUTH`, `PING` cada 5s con `Lock`, `CHECK_HEALTH#<id_ws>` cada 1s, `LEAK` y `RECOVERED`. |
| **Engine de Estación ([`ws/engine/WM_WS_E.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/ws/engine/WM_WS_E.py))** | Persona B (Julián) | **95 %** | Completo. Pendiente pulir: tecla `'m'` (riego manual en estación) y mensajes de `BLOCK` y `ACTIVATE`. |
| **Operario de Campo ([`operator/src/WM_FO.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/operator/src/WM_FO.py))** | Persona B (Julián) | **100 %** | Modo manual interactivo + modo fichero (`servicios_ejemplo.txt`) con espera de 4s entre servicios. |
| **Dockerfiles de WS y FO (`ws/`, `operator/`)** | Persona B (Julián) | **100 %** | `ws/Dockerfile` + `ws/start.sh` y `operator/Dockerfile` + `operator/start.sh`. |
| **Ciclo CI/CD (`VS Code -> GitHub -> Cloud`)** | Ambos | **Pendiente** | Configurar CD hacia la nube (Railway o AWS Learner Lab) y crear workflow opcional `.github/workflows/ci.yml`. |
| **Despliegue Cloud y Pruebas en 2 PCs Lab** | Ambos | **En curso (20-22 Oct)** | Desplegar Central + Kafka en Cloud (**Pendiente de elegir: Railway vs AWS**); probar 2 FO (PC 1) y 2 WS (PC 2) en el laboratorio. |
| **Script / Log `<DNI>SD_Test.log` y Memoria Final** | Ambos | **Pendiente (22-23 Oct)** | Generar log de pruebas, capturas de pantalla, memoria con DNI y merge final a `main`. |

---

## 4. Auditoría contra el Enunciado: CI/CD y Detalles por Pulir

Revisando punto por punto las 14 páginas del PDF oficial de la práctica, estos son los elementos específicos a tener en cuenta:

### 4.1. Ciclo de CI/CD y Plataforma Cloud (Página 13 del Enunciado)
* **Requisito oficial:** *"El ciclo de CI/CD deberá ser: **VS Code -> Github -> Railway** (Aconsejable por su simplicidad) o **VS Code -> Github -> AWS Learner Lab** (Mayor configuración)"*.
* **Estado de la plataforma Cloud:** **Pendiente de selección entre Railway y AWS Learner Lab**:
  * **Opción Railway:** Mayor simplicidad de despliegue automático conectado al repo GitHub. Requiere configurar un TCP Proxy para exponer el puerto de sockets crudos de `WM_Central` y montar un volumen persistente para SQLite en `/data`.
  * **Opción AWS (AWS Learner Lab):** Mayor capacidad y control de configuración (p. ej. desplegando contenedores en EC2 mediante Docker Compose o ECS). Requiere configurar Security Groups (apertura de puertos de sockets, web y Kafka) e IP pública/elástica.
* **Continuous Deployment (CD):** Sea en Railway o en AWS, el despliegue del componente Cloud (`WM_Central`) debe alimentarse del repositorio de GitHub (`jhg45-ua/water-management`) mediante webhook/CD automático o pipeline al hacer `push` a la rama elegida.
* **Continuous Integration (CI) en GitHub Actions (`.github/workflows/ci.yml`):** Conviene crear un workflow que ejecute los tests de sockets ([`tests/test_protocol.py`](file:///Users/julianhinojosagil/Documents/Dev/water-management/tests/test_protocol.py)) y valide el `docker build` de los 3 módulos en cada push.

### 4.2. Detalles Funcionales en `WM_WS_E.py` (Páginas 5, 7 y 8 del Enunciado)
1. **Riego manual desde la propia estación (Pág. 5 y 7):** El enunciado pide que el riego pueda iniciarse *"Manualmente, mediante una opción en la propia estación"*. En [`leer_teclado()`](file:///Users/julianhinojosagil/Documents/Dev/water-management/ws/engine/WM_WS_E.py#L51-L68) están `'k'` (fuga), `'r'` (recuperar) y `'s'` (parar), pero falta añadir una tecla (por ejemplo `'m'`) para solicitar un riego manual en la propia WS.
2. **Mensaje de ayuda de teclado (Línea 53):** Actualizar el texto impreso para mostrar todas las opciones (`k` avería, `r` recuperar, `s` parar suministro, `m` riego manual).
3. **Notificación en pantalla de bloqueo y activación (Pág. 8, punto 11):** Imprimir por pantalla cuando Central envíe `BLOCK` (*"Fuera de Servicio (NARANJA)"*) y `ACTIVATE` (*"Disponible (VERDE)"*).

### 4.3. Requisitos de Entrega y Laboratorio (Páginas 13 y 14 del Enunciado)
* **`README.md`:** Actualmente vacío (0 bytes). Conviene documentar la arquitectura, variables de entorno y comandos Docker.
* **Escenario mínimo de Laboratorio (Figura 4, Pág. 13):** En la evaluación se deben ejecutar al menos **2 instancias de `WM_FO`** en el PC 1 y **2 instancias de `WM_WS`** en el PC 2 contra la nube (Railway o AWS).
* **Entregables en UACloud:** Memoria con portada (DNI de ambos, año académico y título), descripción de componentes y código, guía de despliegue paso a paso, capturas de pantalla y el log `<DNI>SD_Test.log`.

---

## 5. Seguimiento del Calendario e Hitos del Equipo (a 20 de Octubre — 10:06h)

```
[✅ COMPLETADO]  7-9 Oct   : Repo GitHub + Contrato completo en /common (Sockets + Topics/Mensajes Kafka)
[✅ COMPLETADO]  10-13 Oct : Sockets, Auth, BD SQLite, Servidor Central, Panel Web y WM_WS_M
[✅ COMPLETADO]  14-17 Oct : Flujo de riego con Kafka (Central, Engine y FO implementados)
[✅ COMPLETADO]  18-20 Oct : Funcionalidad completa e integración total en la rama 'dev' (sin bugs pendientes)
[🔵 FASE ACTUAL] 21-22 Oct : Selección de plataforma Cloud (Railway vs AWS) + Despliegue + Pruebas en 2 PCs Lab
[⏳ META]        23 Oct    : Cierre, log <DNI>SD_Test.log, carpeta prompts IA, merge a 'main' y memoria
```

---

## 6. Siguientes Pasos (Fase de Pruebas e Integración)

1. **Pruebas End-to-End (E2E) en local con Docker:**
   * Terminal 1: `docker compose up --build` (Kafka + Central).
   * Terminal 2: `docker run -it --rm --network host -e ID_WS=WS-01 wm-ws` (Estación 1).
   * Terminal 3: `docker run -it --rm --network host -e ID_OPERADOR=OP01 wm-fo` (Operario 1).
   * Validar Panel Web en `http://localhost:8080`, prueba de fuga (`k`/`r`) y modo fichero.
2. **Seleccionar plataforma Cloud y configurar el CD:**
   * Evaluar si desplegar en **Railway** (más simple, pero requiere TCP Proxy para sockets) o en **AWS Learner Lab** (mayor control con EC2/Security Groups).
   * Desplegar `WM_Central` + `SQLite` + `Kafka` en la plataforma seleccionada.
3. **Probar la conexión distribuida desde 2 PCs en el Laboratorio.**
4. **Generar `<DNI>SD_Test.log`, recopilar prompts de IA y redactar la memoria final.**
