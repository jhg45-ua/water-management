# Contratos de Arquitectura — Práctica 2 (Water Management)

## 0. Convenciones generales
- **Formato:** JSON (`Content-Type: application/json`), claves y rutas en inglés (`snake_case`).
- **Errores estándar:** todas las respuestas `4xx`/`5xx` devuelven:
  ```json
  { "error": "Descripción breve del error" }
  ```
- **Puertos acordados:**
  - `WM_Registry`: `5001` (**HTTPS** con certificado TLS)
  - `API_Central`: `8000` (**HTTP** + **CORS** habilitado para el Front)
  - `WM_Central` (sockets): `5000`

---

## 1. Contratos API REST

### 1.1 `WM_Registry` (HTTPS `:5001`)

| Método | Ruta | Descripción | Códigos |
|---|---|---|---|
| `POST` | `/registry/stations` | Alta de WS y generación de credencial | `201`, `400`, `409` |
| `DELETE` | `/registry/stations/<ws_id>` | Baja de WS (requiere token en cabecera) | `200`, `401`, `404` |
| `POST` | `/registry/verify` | Verificación de credenciales (desde `WM_Central`) | `200`, `400`, `401` |
| `GET` | `/registry/stations` | Lista de WS registradas (solo metadatos, sin tokens) | `200` |

#### `POST /registry/stations`
- **Request:**
  ```json
  {
    "ws_id": "WS-01",
    "location": "Alicante"
  }
  ```
- **Response `201 Created`:**
  ```json
  {
    "ws_id": "WS-01",
    "location": "Alicante",
    "auth_token": "tok_a8f9c2e1...",
    "registered_at": "2026-11-24T10:00:00Z"
  }
  ```
- **Response `400 Bad Request`:** `{ "error": "Missing ws_id or location" }`
- **Response `409 Conflict`:** `{ "error": "Station WS-01 is already registered" }`

#### `DELETE /registry/stations/<ws_id>`
- **Headers:** `Authorization: Bearer <auth_token>`
- **Body:** *(vacío)*
- **Response `200 OK`:**
  ```json
  {
    "ws_id": "WS-01",
    "deleted": true
  }
  ```
- **Response `401 Unauthorized`:** `{ "error": "Invalid or missing auth_token" }`
- **Response `404 Not Found`:** `{ "error": "Station WS-01 not found" }`

#### `POST /registry/verify`
- **Request:**
  ```json
  {
    "ws_id": "WS-01",
    "auth_token": "tok_a8f9c2e1..."
  }
  ```
- **Response `200 OK`:**
  ```json
  {
    "valid": true,
    "ws_id": "WS-01",
    "location": "Alicante"
  }
  ```
- **Response `401 Unauthorized`:**
  ```json
  {
    "valid": false,
    "error": "Invalid credentials"
  }
  ```
- **Response `400 Bad Request`:** `{ "error": "Missing ws_id or auth_token" }`

#### `GET /registry/stations`
- **Response `200 OK`:**
  ```json
  {
    "stations": [
      {
        "ws_id": "WS-01",
        "location": "Alicante",
        "registered_at": "2026-11-24T10:00:00Z"
      }
    ]
  }
  ```

---

### 1.2 `API_Central` (HTTP `:8000` + CORS)

> **Estados válidos de una WS** (heredados de P1): `ACTIVE`, `WATERING`, `LEAK`, `OUT_OF_SERVICE`, `DISCONNECTED`.

| Método | Ruta | Consumidor | Descripción | Códigos |
|---|---|---|---|---|
| `GET` | `/api/stations` | Front, `WM_W` | Estado completo de todas las WS | `200` |
| `GET` | `/api/stations/<ws_id>` | Front | Detalle de una WS concreta | `200`, `404` |
| `GET` | `/api/operators` | Front | Lista de operarios (FO) y riego activo | `200` |
| `GET` | `/api/waterings` | Front | Lista de riegos en curso | `200` |
| `GET` | `/api/audit` | Front | Log de auditoría, errores y avisos de `WM_W` | `200` |
| `PUT` | `/api/weather/<ws_id>` | `WM_W` | Actualiza clima y activa alerta si procede | `200`, `400`, `404` |
| `DELETE` | `/api/weather/<ws_id>/alert` | `WM_W` | Cancela la alerta climática de la WS | `200`, `404` |
| `POST` | `/api/stations/<ws_id>/commands` | Front | Órdenes manuales (`start`, `block`, `activate`, `revoke_key`) | `200`, `400`, `404` |

#### `GET /api/stations` (y `GET /api/stations/<ws_id>`)
- **Response `200 OK`:**
  ```json
  {
    "stations": [
      {
        "ws_id": "WS-01",
        "location": "Alicante",
        "status": "ACTIVE",
        "registered": true,
        "authenticated": true,
        "key_status": "ACTIVE",
        "key_fingerprint": "a3f9c10b",
        "flow": 0.0,
        "volume": 0.0,
        "total": 142.5,
        "operator": null,
        "pending_weather_stop": false,
        "weather": {
          "city": "Alicante",
          "temp_c": 18.4,
          "condition": "Clear",
          "alert": false,
          "reason": null,
          "updated_at": "2026-11-24T10:05:00Z"
        },
        "last_seen": "2026-11-24T10:05:01Z"
      }
    ]
  }
  ```
  *(Nota: `GET /api/stations/<ws_id>` devuelve directamente el objeto de esa estación o `404 Not Found`.)*

#### `GET /api/operators`
- **Response `200 OK`:**
  ```json
  {
    "operators": [
      {
        "operator_id": "OP01",
        "name": "Operario 1",
        "active_ws": "WS-01"
      }
    ]
  }
  ```

#### `GET /api/waterings`
- **Response `200 OK`:**
  ```json
  {
    "waterings": [
      {
        "ws_id": "WS-01",
        "operator_id": "OP01",
        "flow": 12.5,
        "volume": 37.5,
        "started_at": "2026-11-24T10:04:30Z"
      }
    ]
  }
  ```

#### `GET /api/audit`
- **Query params opcionales:** `?limit=50&source=WM_W&level=ERROR`
- **Response `200 OK`:**
  ```json
  {
    "events": [
      {
        "id": 42,
        "timestamp": "2026-11-24T10:05:00Z",
        "source": "WM_W",
        "actor": "WM_W",
        "ip": "192.168.1.20",
        "action": "WEATHER_ALERT",
        "level": "WARNING",
        "details": "WS-01 (Oslo): temp -2.5C, riego bloqueado"
      }
    ]
  }
  ```

#### `PUT /api/weather/<ws_id>`
- **Request (`WM_W` → `API_Central`):**
  ```json
  {
    "city": "Oslo",
    "temp_c": -2.5,
    "condition": "Snow",
    "alert": true,
    "reason": "Temperature below 0C"
  }
  ```
- **Response `200 OK`:**
  ```json
  {
    "ws_id": "WS-01",
    "weather_alert": true,
    "status": "OUT_OF_SERVICE",
    "pending_weather_stop": false
  }
  ```
- **Response `400 Bad Request`:** `{ "error": "Missing required weather fields" }`
- **Response `404 Not Found`:** `{ "error": "Station WS-01 not found" }`

#### `DELETE /api/weather/<ws_id>/alert`
- **Body:** *(vacío)*
- **Response `200 OK`:**
  ```json
  {
    "ws_id": "WS-01",
    "weather_alert": false,
    "status": "ACTIVE"
  }
  ```
- **Response `404 Not Found`:** `{ "error": "Station WS-01 not found" }`

#### `POST /api/stations/<ws_id>/commands`
- **Request:**
  ```json
  {
    "action": "start",
    "duration": 30
  }
  ```
  *(Valores válidos de `action`: `"start"`, `"block"`, `"activate"`, `"revoke_key"`.)*
- **Response `200 OK`:** `{ "ws_id": "WS-01", "action": "start", "ok": true, "message": "Command executed" }`
- **Response `400 Bad Request`:** `{ "error": "Invalid action" }`
- **Response `404 Not Found`:** `{ "error": "Station WS-01 not found" }`

## 2. Cifrado simétrico (`WM_Central` ↔ `WM_WS_E`)

### 2.1 Algoritmo y justificación
- **Algoritmo:** `Fernet` (librería `cryptography` de Python), basado en **AES-128-CBC + HMAC-SHA256** con IV aleatorio y timestamp.
- **Justificación (teoría SD):**
  - **Confidencialidad:** AES-128 (estándar actual frente a DES/3DES).
  - **Integridad y autenticidad frente a MITM:** HMAC-SHA256 (detecta cualquier alteración lanzando `InvalidToken`).
  - **Frescura contra replay:** timestamp integrado en el token (verificable con `ttl`, p. ej. 60s).
  - **Economía de mecanismos (Kerckhoffs):** estándar abierto sin gestión manual propensa a fallos de padding/IV.
- **Clave:** única por cada WS, generada por `WM_Central` (`Fernet.generate_key()`, string Base64 URL-safe).

### 2.2 Flujo de entrega y revocación de claves
1. `WM_WS_M` se registra en `WM_Registry` por HTTPS (`POST /registry/stations`) y recibe `auth_token`.
2. `WM_WS_M` se autentica en `WM_Central` por socket enviando `AUTH#<ws_id>#<auth_token>`.
3. `WM_Central` valida `ws_id` + `auth_token` contra `WM_Registry` (`POST /registry/verify`).
   - Si es válido: genera una clave `Fernet` única para `ws_id`, la guarda en BD/memoria y responde `AUTH_OK#<fernet_key>`.
   - Si falla: registra evento en auditoría y responde `AUTH_DENIED#<motivo>`.
4. `WM_WS_M` reenvía la clave a su `WM_WS_E` local por el socket Monitor↔Engine (`KEY#<fernet_key>`).
5. **Revocación ("restaurar claves" en Central):** Central elimina la clave de `ws_id` en BD/memoria, pasa la estación a `OUT_OF_SERVICE` y registra auditoría. Todo mensaje cifrado con la clave anterior falla al descifrar y se descarta hasta que `WM_WS_M` se vuelva a autenticar.

### 2.3 Formato del sobre cifrado en Kafka (`wm.ws.commands` y `wm.ws.telemetry`)
Todos los mensajes en los topics entre `WM_Central` y `WM_WS_E` viajan en este sobre JSON:

```json
{
  "ws": "WS-01",
  "encrypted": true,
  "payload": "gAAAAABnQ8x..."
}
```
- `ws`: en claro solo para seleccionar la clave simétrica de esa estación.
- `payload`: JSON original de P1 (`COMMAND` o `TELEMETRY`) cifrado con `Fernet(key)`.
- **Validación tras descifrar:** comprobar que `sobre["ws"] == payload_descifrado["ws"]`.
- **Órdenes globales (`ALL`):** al tener cada WS una clave distinta, `WM_Central` NO publica un mensaje único con `"ws": "ALL"`, sino un sobre cifrado individual por cada WS autenticada usando su propia clave.
- **Ante `InvalidToken` o WS sin clave:** descartar el mensaje y registrar incidente de seguridad en auditoría.

## 3. Esquema de Base de Datos SQLite

### 3.1 `WM_Registry` (`registry.db`)
```sql
CREATE TABLE IF NOT EXISTS registered_stations (
    ws_id         TEXT PRIMARY KEY,
    location      TEXT NOT NULL,
    token_hash    TEXT NOT NULL,     -- SHA-256 hex del auth_token
    registered_at TEXT NOT NULL
);
```

### 3.2 `WM_Central` (`wm.db`)

- **`operators`** *(sin cambios respecto a P1)*:
  ```sql
  CREATE TABLE IF NOT EXISTS operators (
      id   TEXT PRIMARY KEY,
      name TEXT
  );
  ```

- **`stations`** *(ampliada sobre P1)*:
  ```sql
  CREATE TABLE IF NOT EXISTS stations (
      id                   TEXT PRIMARY KEY,
      location             TEXT,
      status               TEXT,
      last_seen            TEXT,
      total                REAL DEFAULT 0,
      registered           INTEGER DEFAULT 0,
      authenticated        INTEGER DEFAULT 0,
      symmetric_key        TEXT,                 -- Clave Fernet única (NULL si revocada/no auth)
      key_status           TEXT DEFAULT 'NONE',  -- NONE | ACTIVE | REVOKED
      city                 TEXT,                 -- Ciudad actual monitorizada por WM_W
      temp_c               REAL,
      weather_condition    TEXT,
      weather_alert        INTEGER DEFAULT 0,    -- 0 = normal, 1 = alerta activa
      weather_reason       TEXT,
      weather_updated_at   TEXT,
      pending_weather_stop INTEGER DEFAULT 0     -- 1 si alerta llegó en mitad de un riego
  );
  ```

- **`audit_logs`** *(nueva tabla — pág. 4 del enunciado)*:
  ```sql
  CREATE TABLE IF NOT EXISTS audit_logs (
      id        INTEGER PRIMARY KEY AUTOINCREMENT,
      timestamp TEXT NOT NULL,
      source    TEXT NOT NULL,   -- CENTRAL | API_CENTRAL | WM_W | WM_WS_M | WM_WS_E | WM_FO
      actor     TEXT NOT NULL,   -- WS-01 | OP01 | WM_W | ADMIN
      ip        TEXT,            -- IP origen (o 'kafka'/'local')
      action    TEXT NOT NULL,   -- AUTH_OK | AUTH_FAIL | KEY_REVOKED | WEATHER_ALERT | WEATHER_CLEAR | LEAK | ...
      level     TEXT DEFAULT 'INFO', -- INFO | WARNING | ERROR | SECURITY
      details   TEXT
  );
  ```