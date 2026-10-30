# Práctica Sistemas Distribuidos: Water Management Network

- **Curso:** 2026/2027
- **Asignatura:** Sistemas Distribuidos
- **Autores:** 
  - Julián Hinojosa (DNI: 48795869N)
  - Héctor García (DNI: 48770607G)

---

## 1. Descripción del proyecto
Este proyecto implementa la simulación de un sistema distribuido para la gestión y monitorización en tiempo real del riego urbano (Water Management). 

Combina dos paradigmas de comunicación:
- **Sockets TCP síncronos** (con empaquetado seguro STX/ETX/LRC) para la autenticación, registro y supervisión de salud entre estaciones y la central.
- **Streaming de eventos asíncrono con Apache Kafka** para el envío de órdenes de riego, telemetría continua de caudal en tiempo real y notificaciones a operarios.
- **Base de datos relacional SQLite** para la persistencia del estado del sistema, estaciones y operarios autorizados.

---

## 2. Componentes y parámetros de ejecución

El sistema está dividido en los siguientes componentes:

### WM_Central (Core System)
Módulo central que coordina la red, gestiona la base de datos SQLite y expone un panel de monitorización web (puerto 8080).
- Escucha conexiones de sockets de los monitores de las estaciones.
- Publica y consume eventos de Kafka para el control del riego.
- Mantiene los estados de cada WS: Disponible (verde), Regando (verde parpadeante), Fuga (rojo), Fuera de servicio (naranja) y Desconectada (gris).

**Ejecución:**
```bash
python3 WM_Central.py <puerto_socket> <ip_kafka:puerto_kafka> [ruta_bd]
```
*Ejemplo:* `python3 WM_Central/WM_Central.py 5000 localhost:9092 WM_Central/database/wm.db`

---

### Watering Station (WS)
Cada estación simula un punto de riego físico y consta de dos procesos:

1. **WM_WS_M (Monitor):**
   - Se conecta por socket a `WM_Central` para autenticar y registrar la estación (ID y ubicación).
   - Abre un socket local para recibir la conexión de su `WM_WS_E` (Engine).
   - Envía cada segundo una comprobación de salud (heartbeat). Si el Engine no responde o reporta KO, envía a la Central un aviso de avería (fuga).

   **Ejecución:**
   ```bash
   python3 ws/monitor/WM_WS_M.py <puerto_engine> <ip_central:puerto_central> <id_ws> [ubicacion] [protocolo]
   ```
   *Ejemplo:* `python3 ws/monitor/WM_WS_M.py 6001 localhost:5000 WS-01 "Parque Central" lrc`

2. **WM_WS_E (Engine):**
   - Se conecta al socket local del Monitor y al bus de eventos Kafka.
   - Al activarse un riego, abre la electroválvula simulada y publica cada segundo el caudal (litros/min) y volumen acumulado.
   - En ejecución permite pulsar una tecla en la consola para simular una avería y reportar un KO al Monitor.

   **Ejecución:**
   ```bash
   python3 ws/engine/WM_WS_E.py <ip_kafka:puerto_kafka> <ip_monitor:puerto_monitor> [protocolo]
   ```
   *Ejemplo:* `python3 ws/engine/WM_WS_E.py localhost:9092 localhost:6001 lrc`

---

### WM_FO (Field Operators)
Aplicación de consola utilizada por los operarios de mantenimiento para solicitar el riego de una estación.
- **Modo manual:** Permite seleccionar la estación y la duración directamente desde un menú.
- **Modo fichero:** Lee una lista de peticiones desde un archivo de texto (ej. `servicios_ejemplo.txt`), esperando 4 segundos entre servicios.

**Ejecución:**
```bash
python3 operator/src/WM_FO.py <ip_kafka:puerto_kafka> <id_operador> [fichero_servicios]
```
*Ejemplos:*
```bash
# Modo manual interactivo
python3 operator/src/WM_FO.py localhost:9092 OP01

# Modo por fichero de comandos
python3 operator/src/WM_FO.py localhost:9092 OP01 operator/servicios_ejemplo.txt
```

---

## 3. Protocolos de comunicación (Sockets)

El proyecto incluye una arquitectura modular extensible basada en la interfaz abstracta `BaseProtocol` (`common/protocol/base.py`), ofreciendo dos implementaciones intercambiables:

1. **Protocolo Estándar LRC (`StandardLRCProtocol`, opción por defecto `lrc`):**
   - Recomendado en la especificación oficial de la práctica.
   - Formato de trama: `<STX><DATA><ETX><LRC>`.
   - `STX` (byte `0x02`, inicio de texto) y `ETX` (byte `0x03`, fin de texto).
   - `LRC` (*Longitudinal Redundancy Check*): Checksum XOR byte a byte del mensaje de datos para validar su integridad a nivel de aplicación.
   - Control de flujo y sincronización mediante tramas de saludo y confirmación (`<ENQ>`, `<ACK>`, `<NACK>` y `<EOT>`).

2. **Protocolo Delimitado por Línea (`LineDelimitedProtocol`, opción `line`):**
   - Protocolo alternativo ligero y de alto rendimiento basado en saltos de línea (`\n`).
   - Comunicación directa y sin sobrecarga de tramas de control, confiando la integridad de los paquetes a las garantías nativas del protocolo de transporte TCP.
   - Propuesta de mejora del equipo para comparar en el benchmark la reducción de sobrecarga frente al protocolo estándar.

Ambos protocolos son intercambiables dinámicamente mediante el argumento `[protocolo]` (`lrc` o `line`) al lanzar `WM_Central.py`, `WM_WS_M.py` o mediante la variable de entorno `PROTO=line` en Docker.

Adicionalmente, se incluye la suite comparativa `tests/benhmark_protocol.py` que permite medir el tiempo total, la latencia media (ms) y el *throughput* (req/s) de ambos protocolos.

---

## 4. Guía de despliegue

### Despliegue en entorno local (Docker)

1. **Arrancar Kafka y Central:**
   ```bash
   docker compose up -d
   ```
   El panel de monitorización quedará accesible en `http://localhost:8080`.

2. **Arrancar N Estaciones de Riego:**
   Se proporciona el script `launch_ws.sh` que levanta estaciones configuradas en contenedores interactivos:
   ```bash
   ./launch_ws.sh 3         # Lanza WS-01, WS-02 y WS-03
   ./launch_ws.sh status    # Muestra el estado de las estaciones
   ./launch_ws.sh stop      # Detiene todas las estaciones
   ```
   *Para interactuar o simular una avería por teclado:*
   ```bash
   docker attach ws-01      # Pulsar 'k' avería, 'r' recuperar, 'm [seg]' riego manual (Salir: Ctrl+P, Ctrl+Q)
   ```

3. **Arrancar Operario (WM_FO):**
   ```bash
   # Construir imagen del operario si no existe:
   docker build -t wm-fo -f operator/Dockerfile .

   # Modo interactivo mediante Docker:
   docker run -it --rm --network water-management_default \
     -e KAFKA_SERVERS=kafka:19092 -e ID_OPERADOR=OP01 wm-fo
   ```

---

### Despliegue distribuido para evaluación (Escenario de laboratorio)

Siguiendo el esquema obligatorio del enunciado (Cloud + Laboratorio con 2 PCs):

1. **Cloud (AWS):**
   - Despliegue de **Kafka** y **WM_Central** con base de datos SQLite en volumen persistente (`/data/wm.db`).
   - `WM_Central` expone su puerto de sockets (5000) y el panel web (8080) públicamente.

2. **PC LAB 1 (Operarios):**
   - Ejecución de las instancias de `WM_FO` apuntando al Kafka desplegado en AWS:
     ```bash
     # Construir imagen (si se ejecuta por primera vez):
     docker build -t wm-fo -f operator/Dockerfile .

     # Modo manual interactivo con Docker (obligatorio según pág. 13 del enunciado):
     docker run -it --rm \
       -e KAFKA_SERVERS="<HOST_AWS>:9092" \
       -e ID_OPERADOR="OP01" \
       wm-fo

     # Modo automático por fichero de comandos (lote de pruebas):
     docker run -it --rm \
       -e KAFKA_SERVERS="<HOST_AWS>:9092" \
       -e ID_OPERADOR="OP02" \
       -e FICHERO_SERVICIOS="operator/servicios_evaluacion.txt" \
       wm-fo
     ```

3. **PC LAB 2 (Estaciones de riego):**
   - Ejecución masiva automatizada con el script parametrizado para AWS:
     ```bash
     CENTRAL_ADDR="<HOST_AWS>:5000" KAFKA_SERVERS="<HOST_AWS>:9092" ./launch_ws.sh 2
     ```
   - O bien despliegue individual contenedor por contenedor:
     ```bash
     docker run -dit --name ws-01 \
       -e CENTRAL_ADDR="<HOST_AWS>:5000" \
       -e KAFKA_SERVERS="<HOST_AWS>:9092" \
       -e ID_WS="WS-01" \
       -e LOCATION="Parque Norte" \
       water-management-ws
     ```

---

## 5. Estructura del repositorio

```text
├── WM_Central/         # Servidor central, base de datos SQLite y panel web
├── ws/                 # Estación de riego (Monitor WM_WS_M y Engine WM_WS_E)
├── operator/           # Aplicación del operario WM_FO y ficheros de servicios
├── common/             # Protocolo sockets STX/ETX/LRC, serialización y tópicos
├── launch_ws.sh        # Script bash para automatizar el despliegue de estaciones
├── docker-compose.yml  # Definición de servicios para Kafka y Central
├── prompts/            # Registro de prompts de IA según la normativa de la práctica
└── tests/              # Pruebas unitarias y benchmarks de sockets
```
