# Fleet OBD Platform - Complete System Wiring Map

---

## 1. ARCHITECTURE OVERVIEW (COMPLETE WIRING DIAGRAM)

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                                   PHYSICAL LAYER                                          │
│                                                                                          │
│  ELM327 BLE OBD-II Dongle (in vehicle OBD port)                                          │
│         │                                                                                │
│         ▼ Bluetooth LE                                                                   │
│  ┌──────────────────────────────────────────────────────────────────────────────┐       │
│  │                    REACT NATIVE MOBILE APP (FleetMobile/)                     │       │
│  │                                                                               │       │
│  │  BLE Manager (ble-plx) → OBD Manager (ELM327 AT commands) → Telemetry Streamer      │
│  │                                                                               │       │
│  │  ┌─────────────────┐    ┌──────────────────────┐    ┌─────────────────────┐   │       │
│  │  │  BLE Scanner     │    │  OBD-II Parser       │    │  MQTT Publisher    │   │       │
│  │  │  (react-native-  │───▶│  (ELM327 AT cmds)    │───▶│  (QoS 1)          │   │       │
│  │  │   ble-plx)       │    │                      │    │  ws://host:8083   │   │       │
│  │  └─────────────────┘    └──────────────────────┘    └─────────┬───────────┘   │       │
│  └──────────────────────────────────────────────────────────────────┼────────────┘       │
│                                                                     │                    │
│                                                                     │ MQTT (WebSocket)   │
│                                                                     │ telemetry/{car_id} │
│                                                                     ▼                    │
│  ┌────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                     INFRASTRUCTURE LAYER (docker-compose.yml)                     │  │
│  │                                                                                   │  │
│  │  ┌──────────────┐   ┌──────────────┐   ┌───────────────┐   ┌───────────────┐     │  │
│  │  │  TimescaleDB  │   │   Redis 7    │   │  EMQX 5.5.0  │   │    Nginx      │     │  │
│  │  │  :5432        │   │  :6379       │   │  :1883/8083  │   │  (optional)   │     │  │
│  │  │  ^postgres:5432│   │  ^redis:6379 │   │  ^mqtt:1883  │   │               │     │  │
│  │  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘   └───────────────┘     │  │
│  └─────────┼──────────────────┼──────────────────┼─────────────────────────────────┘  │
│            │                  │                  │                                    │
│            ▼                  ▼                  ▼                                    │
│  ┌────────────────────────────────────────────────────────────────────────────────┐    │
│  │                          APPLICATION LAYER (backend/)                         │    │
│  │                                                                               │    │
│  │  ┌──────────────────────────────────────────┐                                 │    │
│  │  │          FastAPI Backend (:8000)          │                                 │    │
│  │  │                                          │                                 │    │
│  │  │  ┌──────────────────────────────────────┐│                                 │    │
│  │  │  │  LIFESPAN (startup sequence):        ││                                 │    │
│  │  │  │  1. DB Connection check              ││                                 │    │
│  │  │  │  2. Redis client connect             ││                                 │    │
│  │  │  │  3. WebSocket manager start          ││                                 │    │
│  │  │  │  4. MQTT client connect + subscribe  ││                                 │    │
│  │  │  │     (telemetry/#, obd/#)             ││                                 │    │
│  │  │  └──────────────────────────────────────┘│                                 │    │
│  │  │                                          │                                 │    │
│  │  │  API ROUTES:                            │                                 │    │
│  │  │  POST /api/v1/auth/*                     │                                 │    │
│  │  │  POST /api/v1/telemetry/ingest           │                                 │    │
│  │  │  GET  /api/v1/telemetry/history          │                                 │    │
│  │  │  GET  /api/v1/telemetry/latest/{id}      │                                 │    │
│  │  │  WS   /api/v1/ws                         │                                 │    │
│  │  │  GET  /api/v1/alerts/*                   │                                 │    │
│  │  │  POST /api/v1/ai/*                       │                                 │    │
│  │  │  POST/GET /api/v1/fleet/*                │                                 │    │
│  │  └──────────────────────────────────────────┘                                 │    │
│  │                                                                               │    │
│  │  ┌──────────────────────────────────────────────────────────┐                 │    │
│  │  │              BACKGROUND TASKS (Celery)                    │                 │    │
│  │  │                                                          │                 │    │
│  │  │  celery_worker (concurrency=2)                           │                 │    │
│  │  │  ├─ default queue:                                      │                 │    │
│  │  │  │  └─ threshold_checker.check_thresholds               │                 │    │
│  │  │  │  └─ anomaly_detector.detect_anomalies                │                 │    │
│  │  │  ├─ aggregation queue:                                  │                 │    │
│  │  │  │  └─ data_aggregator.aggregate_hourly_data            │                 │    │
│  │  │  └─ ai queue:                                           │                 │    │
│  │  │     └─ ai_tasks.trigger_ai_diagnostic                   │                 │    │
│  │  │     └─ ai_tasks.trigger_ai_analysis                     │                 │    │
│  │  │                                                          │                 │    │
│  │  │  celery_beat (scheduled tasks)                           │                 │    │
│  │  │  ├─ :05 hourly → aggregate_hourly_data                  │                 │    │
│  │  │  ├─ :30 hourly → process_geofence_locations             │                 │    │
│  │  │  ├─ 01:00 daily → generate_daily_fleet_summary         │                 │    │
│  │  │  ├─ 02:00 daily → calculate_daily_driver_scores        │                 │    │
│  │  │  ├─ 03:00 daily → run_fuel_anomaly_detection           │                 │    │
│  │  │  ├─ 04:00 Sun → run_maintenance_predictions            │                 │    │
│  │  │  └─ 06:00 daily → generate_fleet_report                │                 │    │
│  │  └──────────────────────────────────────────────────────────┘                 │    │
│  └────────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                          │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│                              FRONTEND LAYER                                              │
│                                                                                          │
│  ┌─────────────────────┐              ┌─────────────────────┐                           │
│  │  Next.js Dashboard  │              │  React Native App  │                           │
│  │  :3000              │              │  (same WS/MQTT)    │                           │
│  │                     │              │                     │                           │
│  │  REST API calls     │              │  BLE + OBD-II read  │                           │
│  │  WebSocket client   │              │  MQTT publish       │                           │
│  │  (Ant Design UI)    │              │  WebSocket listen   │                           │
│  └─────────────────────┘              └─────────────────────┘                           │
│                                                                                          │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│                           AI LAYER (Optional)                                           │
│                                                                                          │
│  LM Studio (host.docker.internal:1234/v1) or Ollama (:11434)                            │
│  └─ OpenAI-compatible chat completions API                                              │
│     └─ Circuit breaker pattern with DTC fallback map                                    │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. COMPLETE DATA FLOW - TELEMETRY PIPELINE

### Flow A: MQTT Path (Primary - Real-time from Mobile)

```
Step 1: [Mobile App] ELM327 BLE → OBD-II Parser
        Reads PIDs: RPM, Speed, Coolant Temp, Engine Load, 
        Fuel Level/Rate/Pressure, MAF, O2, DTC codes, GPS lat/lng
        ↑ Sends AT commands via BLE to ELM327 dongle
        ↓ Parses hex responses into numerical values

Step 2: [Mobile App] MQTT Publisher → EMQX Broker
        URL: ws://<host>:8083   (WebSocket MQTT transport)
        Topic: telemetry/{car_id}   (QoS 1)
        Payload: JSON object with all OBD fields + GPS + timestamp

Step 3: [EMQX Broker] Routes message to subscribers
        QoS 1 → at-least-once delivery, duplicate possible
        Retained messages: No (not configured)
        Persistence: Memory (no file persistence configured)

Step 4: [FastAPI MQTT Wrapper - mqtt_client.py] _on_message callback
        - gmqtt client subscribed to: telemetry/#, obd/#
        - Decodes JSON payload
        - Extracts car_id from topic (telemetry/{uuid})
        - Loads car organization from DB cache (car_org_cache dict)
        - Creates TelemetryIngestRequest Pydantic model
        - Calls TelemetryService.ingest_telemetry()

Step 5: [TelemetryService] Database write
        - Verifies car exists + belongs to organization
        - Creates OBDData record (TimescaleDB hypertable)
        - Commits to database
        - Broadcasts to WebSocket via manager.broadcast_to_car()
          → Redis PubSub channel: ws:car:{car_id}
          → Local WebSocket connections in room car:{car_id}

Step 6: [WebSocket Manager] Real-time delivery
        - Publishes to Redis channel (for cross-instance)
        - Sends to all local WS connections subscribed to car room
        - Cleans up disconnected sockets
        - Heartbeat loop: pings every 30s, timeout at 60s
```

### Flow B: REST API Path (Alternative - Web Dashboard/3rd Party)

```
Step 1: HTTP POST /api/v1/telemetry/ingest
        Auth: JWT Bearer token (user) OR X-API-Key header (device)
        Body: TelemetryIngestRequest JSON
        
Step 2: Middleware validates auth
        get_current_user() → JWT decode → SQLAlchemy User lookup
        OR get_current_device() → SHA256 hash API key → DB lookup
        
Step 3: Same as Flow A Step 5-6 (TelemetryService + WebSocket broadcast)
```

### Flow C: Celery Background Processing

```
Triggered after each telemetry ingest (chained via Celery .delay()):
       │
       ├──→ threshold_checker.check_thresholds()
       │      Checks: coolant_temp (100/110°C), engine_load (90%), speed (150 km/h), DTC codes
       │      Creates Alert records in DB
       │      Broadcasts alerts via WebSocket
       │      If DTC: triggers ai_tasks.trigger_ai_diagnostic()
       │
       └──→ anomaly_detector.detect_anomalies()
              Z-score calculation vs 7-day baseline
              Metrics: rpm, speed, coolant_temp, fuel_rate, engine_load
              Threshold: z-score > 3.0
              Creates Anomaly alerts
              If 2+ anomalies: triggers ai_tasks.trigger_ai_analysis()
```

### Flow D: Scheduled Batch Processing

```
Hourly:
  data_aggregator.aggregate_hourly_data()
    → Aggregates raw OBDData into OBDDataHourly (avg, max, sum)
    → Distance = avg_speed / 60 km (approximation)
    → Fuel consumed = fuel_rate L (approximation)
    → DTC count = sum(array_length(dtc_codes))

Every 30 min:
  fleet_tasks.process_geofence_locations()
    → Gets latest GPS for each active car
    → Checks against geofence polygons/radius
    → Creates GeofenceEvent for enter/exit
    → Broadcasts via WebSocket

Daily at 01:00 UTC:
  data_aggregator.generate_daily_fleet_summary()
    → Per-org: active cars, total distance, fuel, avg speed, DTC count

Daily at 02:00 UTC:
  fleet_tasks.calculate_daily_driver_scores()
    → Safety score, efficiency score, overall score
    → Metrics: trips, distance, harsh braking, speeding, idle time

Daily at 03:00 UTC:
  fleet_tasks.run_fuel_anomaly_detection()
    → For each car: analyze_fuel_consumption(7 days) + check_idle_fuel_theft(24h)

Weekly Sunday 04:00 UTC:
  fleet_tasks.run_maintenance_predictions()
    → Predicts maintenance needs from telemetry patterns

Daily at 06:00 UTC:
  fleet_tasks.generate_fleet_report()
    → Per-org report: total cars, active cars, alerts, distance
    → Broadcasts to org admin WebSocket room
```

---

## 3. DATABASE SCHEMA WIRING

### TimescaleDB Hypertables

```
obd_data (Hypertable - partitioned by time)
├── time (DateTime, PK) - partition key
├── car_id (UUID, PK) - ForeignKey → cars.id
├── organization_id (UUID, FK → organizations.id)
├── rpm (Integer, nullable)
├── speed (Integer, nullable)
├── throttle_position (Float)
├── engine_load (Float)
├── coolant_temp (Integer)
├── intake_temp (Integer)
├── fuel_level (Float)
├── fuel_rate (Float)
├── fuel_pressure (Float)
├── maf_rate (Float)
├── o2_voltage (Float)
├── latitude (Numeric(10,6))
├── longitude (Numeric(10,6))
├── dtc_codes (ARRAY(String), GIN index)
├── mil_status (Boolean)
├── raw_data (JSONB) - full original payload
└── Indexes: (org_id, time), (car_id, time), GIN on dtc_codes

obd_data_hourly (Regular Table)
├── time (DateTime, PK) - hour bucket
├── car_id (UUID, PK)
├── organization_id (UUID, FK)
├── avg_rpm, avg_speed, max_speed, avg_throttle
├── avg_engine_load, avg_coolant_temp, avg_fuel_rate
├── total_distance_km (Numeric(10,3))
├── total_fuel_consumed_l (Numeric(10,3))
├── dtc_count (Integer)
└── Unique: (time, car_id)
```

### Relational Tables

```
organizations          users                   cars
├── id (UUID, PK)      ├── id (UUID, PK)       ├── id (UUID, PK)
├── name               ├── org_id (FK)         ├── org_id (FK)
├── slug               ├── email (Unique)      ├── vin (Unique, 17 chars)
├── settings (JSONB)   ├── password_hash       ├── license_plate
└── is_active          ├── full_name           ├── make, model, year
                        ├── role (Enum)        ├── assigned_driver_id (FK)
                        │   admin              ├── metadata (JSONB)
                        │   fleet_manager      └── is_active
                        │   driver
                        └── is_active
                              │
 devices                refresh_tokens         device_api_keys
 ├── id (UUID, PK)      ├── id (UUID, PK)      ├── id (UUID, PK)
 ├── car_id (FK)        ├── user_id (FK)       ├── org_id (FK)
 ├── mac_address        ├── token_hash          ├── car_id (FK)
 ├── device_type        ├── family_id           ├── key_hash
 └── firmware_ver       ├── is_revoked          ├── name
                         └── expires_at         └── is_active

alerts                  messages               ai_sessions
├── id (UUID, PK)       ├── id (UUID, PK)      ├── id (UUID, PK)
├── org_id (FK)         ├── org_id (FK)        ├── org_id (FK)
├── car_id (FK)         ├── scope (car/org)    ├── car_id (FK)
├── alert_type (Enum)   ├── car_id (FK)        ├── user_id (FK)
├── severity (Enum)     ├── message_type       ├── session_type
├── title               ├── sender_type        ├── prompt
├── message             ├── content (Text)     ├── response
├── metadata (JSONB)    ├── metadata (JSONB)   ├── tokens_used
├── is_read              └── created_at         ├── processing_time_ms
└── is_resolved                                 └── model_used

geofences               geofence_events       maintenance_schedules
├── id (UUID, PK)       ├── id (UUID, PK)     ├── id (UUID, PK)
├── org_id (FK)         ├── org_id (FK)       ├── org_id (FK)
├── name                ├── geofence_id (FK)  ├── car_id (FK)
├── geofence_type       ├── car_id (FK)       ├── maintenance_type
├── geometry (JSONB)    ├── event_type        ├── status
├── notify_on_entry     ├── event_time        ├── scheduled_date
├── notify_on_exit      └── location (JSONB)  └── estimated_cost
└── is_active

driver_scores           fuel_anomalies        maintenance_predictions
├── id (UUID, PK)       ├── id (UUID, PK)     ├── id (UUID, PK)
├── user_id (FK)        ├── org_id (FK)       ├── org_id (FK)
├── org_id (FK)         ├── car_id (FK)       ├── car_id (FK)
├── period_start        ├── anomaly_type      ├── maintenance_type
├── period_end          ├── severity          ├── predicted_days
├── overall_score       ├── expected_fuel     ├── confidence_score
├── safety_score        ├── actual_fuel       └── reasoning (Text)
├── efficiency_score    ├── is_confirmed
└── (harsh_braking,     └── is_investigated
     speeding, etc.)
```

---

## 4. AUTHENTICATION & AUTHORIZATION WIRING

### Auth Flows

```
User Login:
  POST /api/v1/auth/login
  → authenticate_user() checks email + bcrypt(password)
  → Returns: access_token (15min JWT) + refresh_token (7 days)
  → refresh_token stored in DB (SHA256 hash, family_id for rotation)

Token Refresh:
  POST /api/v1/auth/refresh
  → decode old refresh_token
  → check hash in DB, not revoked, not expired
  → revoke old token
  → issue new token (same family_id)
  → If reuse detected: revoke entire family (token theft protection)

Device API Key:
  X-API-Key header
  → SHA256 hash → DB lookup → validate is_active
  → Car-scoped access (belongs to specific car)
  → Used for automated telemetry ingestion

WebSocket Auth:
  /api/v1/ws?token=<jwt>
  → decode_token → extract user_id + organization_id
  → DB lookup → validate user exists + is_active
  → Subscribe to rooms based on role:
     - admin/fleet_manager: org:{org_id} (all cars)
     - driver: only assigned cars car:{car_id}
```

---

## 5. WEB SOCKET MESSAGING MAP

### Connection Lifecycle
```
Client → Server: WS /api/v1/ws?token=<jwt>
Server → Client: accept (HTTP 101)
Server: subscribe to org:{org_id}, user:{user_id}
Server: heartbeat loop every 30s

Client Messages:
┌────────────────────┬──────────────────────────────────────────────┐
│ {"type":"ping"}    │ Keep-alive → server responds {"type":"pong"} │
│ {"type":"subscribe",│ Subscribe to additional room (e.g. car:uuid) │
│  "room":"car:uuid"}│                                              │
│ {"type":"unsubscribe",│ Unsubscribe from room                     │
│  "room":"car:uuid"}│                                              │
└────────────────────┴──────────────────────────────────────────────┘

Server Messages:
┌─────────────────────────────┬────────────────────────────────────┐
│ {"type":"telemetry",        │ Real-time OBD data broadcast       │
│  "car_id":"...", "data":{}}│                                       │
│ {"type":"alert",            │ New alert created                  │
│  "data":{...}}              │ (threshold, anomaly, DTC, etc.)    │
│ {"type":"ai_reply",         │ AI response to chat/diagnostic     │
│  "data":{...}}              │                                       │
│ {"type":"geofence_event",   │ Vehicle entered/exited geofence    │
│  "data":{...}}              │                                       │
│ {"type":"message",          │ Chat/system message                │
│  "data":{...}}              │                                       │
│ {"type":"daily_report",     │ Daily fleet summary report         │
│  "data":{...}}              │                                       │
│ {"type":"alert_resolved",   │ Alert resolved by user             │
│  "data":{...}}              │                                       │
│ {"type":"pong"}             │ Response to client ping            │
└─────────────────────────────┴────────────────────────────────────┘
```

---

## 6. FAILURE MODES & RISK ANALYSIS

### Critical Single Points of Failure

| Component | Failure Mode | Impact | Mitigation |
|-----------|-------------|--------|------------|
| **EMQX Broker** | Crash/Network loss | All MQTT telemetry lost - no vehicle data flowing | MQTT client has reconnection loop (1s-60s backoff). But NO persistent queue - messages during downtime are lost |
| **Redis** | Crash/Restart | WebSocket pub/sub dead, Celery broker dead, rate limiter dead, session cache lost | Redis has append-only persistence. But no Sentinel/Cluster. Full outage = WS rooms lost |
| **Postgres/TimescaleDB** | Crash | All writes fail, auth fails, history queries fail | Connection pool (20-40 connections). No read replicas. No failover. |
| **Single Celery Worker** | Crash | Tasks queued but not processed | `concurrency=2`, but only 1 worker container. No worker pool scaling. |
| **MQTT Client (in FastAPI)** | Crash/lost connection | MQTT→DB pipeline dead until reconnection succeeds | Reconnect loop, but resubscribes to topics. Messages sent during disconnect are lost. |
| **WebSocket Manager** (in-memory) | FastAPI restart | ALL WebSocket connections lost, room subscriptions lost, users must reconnect | Redis pub/sub for cross-instance. But no reconnection state recovery on server side. |

### Detailed Failure Scenarios

#### 6.1 MQTT Message Loss
- **Problem**: Mobile app publishes to EMQX at QoS 1 (at-least-once). If FastAPI MQTT client disconnects between message and acknowledgment, message is redelivered - could cause duplicate DB entries.
- **Impact**: Duplicate telemetry records (OBDData has `UniqueConstraint(time, car_id)` - BUT if time differs by microseconds, duplicates pass through).
- **Detection**: Not currently monitored. No MQTT dead-letter queue.
- **Fix Needed**: Add message deduplication (message ID), set up EMQX persistence/retain, add monitoring dashboard.

#### 6.2 Celery Task Overload at 1000 Users
- **Problem**: Each telemetry ingest triggers `check_thresholds` + `detect_anomalies` as Celery tasks. At 1000 cars, at 1Hz each = 1000 ingests/sec = 2000 Celery tasks/sec.
- **Impact**: Celery queue grows unbounded. Tasks timeout (5 min soft, 10 min hard). Redis memory fills. Tasks get dropped after max_retries.
- **Bottleneck**: `concurrency=2` worker can process ~20 tasks/sec. 2000/sec = 100x overload.
- **Fix Needed**: Batch processing, async threshold checking inline, reduce anomaly detection frequency, increase concurrency, add worker auto-scaling.

#### 6.3 Database Write Contention
- **Problem**: 1000 cars × 1Hz = 1000 writes/sec to `obd_data` hypertable. Each write requires `select Car` verification + `insert OBDData` + `commit`.
- **Impact**: Connection pool (20-40) exhausted. Write queue builds. TimescaleDB compression policy (7-day) may conflict with active writes.
- **Fix Needed**: Batch inserts (10-50 per commit), reduce write frequency for non-critical cars, add read replicas, increase pool size.

#### 6.4 WebSocket Scalability
- **Problem**: Each dashboard user opens 1 WS connection. Each telemetry write broadcasts to car room - if 10 users watch same car, 10× amplification.
- **Impact**: For 1000 users watching 1000 cars (1 each): 1000 WS connections. Each telemetry write = Redis pub + N WS sends. Server memory grows with connections.
- **Fix Needed**: WS connection limits, add horizontal scaling (multiple FastAPI instances behind load balancer), limit rooms per user.

#### 6.5 LLM/AI Service Dependency
- **Problem**: AI calls to LM Studio/Ollama have 120s timeout. Circuit breaker opens after 3 failures (60s recovery). DTC detection triggers AI.
- **Impact**: If LLM is slow/down, Celery tasks hang for 120s, queue fills. Circuit breaker causes all AI features to fail silently.
- **Fix Needed**: Async non-blocking AI, separate worker pool for AI tasks, better fallback with cached DTC explanations.

#### 6.6 Mobile App Edge Cases
- **Problem**: BLE disconnections, network changes (WiFi↔Cellular), app background state.
- **MQTT QoS**: Cellular interval is 15s, offline is 30s - but MQTT connection drops on network change.
- **Impact**: Data gaps, stale telemetry shown on dashboard, missed alerts.
- **Fix Needed**: MQTT session persistence (clean_session=false), local storage queuing, last will message for disconnection detection.

#### 6.7 Refresh Token Reuse Attack
- **Problem**: If a refresh token is stolen and used by attacker AND legitimate user, family_id detection kicks in - ALL tokens revoked.
- **Impact**: User forcibly logged out on all devices. They see "session expired" with no explanation.
- **Fix Needed**: Add user notification when token family revoked, allow manual re-auth without data loss.

#### 6.8 API Key Exposure
- **Problem**: Device API keys are generated via `secrets.token_urlsafe(32)` (256-bit). But:
  - No key rotation policy
  - Key shown once at creation (can't recover)
  - No IP restriction/rate limiting per key
- **Impact**: Leaked key = unlimited access to ingest telemetry for that car.
- **Fix Needed**: Add key rotation, usage quotas, IP allow-listing, audit logging.

#### 6.9 CORS Configuration
- **Problem**: In development, CORS allows `*` (via middleware). In production, `CORS_ORIGINS` must be set or app crashes on startup.
- **Impact**: If `CORS_ORIGINS` env var missing in prod: `RuntimeError: CORS_ORIGINS must be set in production`. App won't start.
- **Fix Needed**: Validate .env.prod configuration, add startup test for required variables.

#### 6.10 Prometheus Metrics Endpoint
- **Problem**: `/metrics` is exposed on the same port as the API (8000) with no authentication.
- **Impact**: Anyone who can reach the API can see all internal metrics (request rates, error rates, etc.).
- **Fix Needed**: Add basic auth or separate metrics port.

---

## 7. PERFORMANCE BOTTLENECKS FOR 1000 USERS

### By Component

```
FastAPI Backend (1 instance)
├── CPU: ~2 cores (per docker-compose)
├── DB Pool: 20 connections (max_overflow: 40 total)
├── WS Connections: 1 per user = 1000 sockets (memory ~1-2MB each = 1-2GB)
├── MQTT Subscriber: Single thread processing all messages
└── Request throughput: ~500 req/s limit (per instance)

TimescaleDB (1 instance)
├── Write throughput: ~5000 inserts/s (with batching)
├── Read throughput: ~1000 queries/s
├── Connection limit: not configured (default 100)
└── Storage: depends on retention (need data lifecycle policy)

Redis (1 instance)
├── Pub/Sub: no message persistence
├── List length: Celery broker (unbounded queue)
├── Memory: Celery result backend (24h retention)
└── Throughput: ~100K ops/s (but single-threaded)

Celery (1 worker, concurrency=2)
├── Tasks/sec: ~20 (each task opens new DB session)
├── Queue depth: could reach millions under load
└── No rate limiting on task creation

EMQX (1 instance)
├── MQTT connections: default max 1024 (needs increase)
├── Sessions: in-memory (no persistence configured)
└── Messages/sec: ~100K (theoretical, not bottleneck)
```

### Critical Ratios for 1000 Cars at 1Hz

```
Raw data rate:         1000 msgs/sec = 1,440,000 msgs/day
Database writes:       1000 inserts/sec (peak)
Celery tasks/sec:      2000 tasks/sec (2 tasks per ingest)
DB connections used:   1000+ (each task opens new session)
WS broadcasts:         1000 broadcasts/sec (to subscriber rooms)
Memory (WS):          ~1-2GB for connections
CPU (DB+API+WS):      ~4-8 cores required for real-time
```

---

## 8. CONFIGURATION GAPS & BUGS FOUND

### Critical Bugs

1. **Duplicate MQTT_URL fields in settings.py** (lines 22, 30):
   ```python
   MQTT_URL: str = Field(default="mqtt://localhost:1883", env="MQTT_URL")  # line 22
   MQTT_USERNAME: Optional[str] = Field(None, env="MQTT_USERNAME")         # line 23
   MQTT_PASSWORD: Optional[str] = Field(None, env="MQTT_PASSWORD")         # line 24
   # ... fields 25-29 ...
   MQTT_URL: str = Field(default="mqtt://localhost:1883", env="MQTT_URL")  # line 30 (DUPLICATE!)
   MQTT_USERNAME: Optional[str] = Field(None, env="MQTT_USERNAME")         # line 31 (DUPLICATE!)
   MQTT_PASSWORD: Optional[str] = Field(None, env="MQTT_PASSWORD")         # line 32 (DUPLICATE!)
   ```
   **Impact**: Pydantic will use the LAST declaration. No functional bug but wastes developer time.

2. **Celery tasks create new DB sessions inside asyncio.run()**
   ```python
   # Pattern repeated in ALL Celery tasks
   async def _check_thresholds():
       from backend.db.session import AsyncSessionLocal  # fresh import each time
       async with AsyncSessionLocal() as db:  # opens NEW connection
           ...
   asyncio.run(_check_thresholds())
   ```
   **Impact**: Each Celery task opens a NEW database connection. At 2000 tasks/sec, this exhausts the DB connection pool. Should use shared engine with connection pooling.

3. **Celery task imports within functions** (late import pattern):
   `from backend.db.session import AsyncSessionLocal` inside `_check_thresholds()` - prevents proper registration, slows task execution, can cause import errors in production.

4. **WebSocket get_db() anti-pattern**:
   ```python
   async for db_session in get_db():
       db = db_session
       break
   ```
   **Impact**: The generator is consumed incompletely. The session context manager's cleanup may not fire properly, causing connection leaks.

5. **MQTT message without deduplication**:
   QoS 1 redelivered messages create duplicate records. The UniqueConstraint on (time, car_id) won't catch duplicates with microsecond differences.

### Configuration Warnings

6. **JWT_SECRET is hardcoded in .env.docker**: `a1b2c3d4e5f6...` - In production, must be a proper random secret.

7. **PostgreSQL port mapping**: Container port 5432 → host 5433 (not 5432). Developers may accidentally connect to different PostgreSQL instances.

8. **Redis port mapping**: Container port 6379 → host 6380.

9. **Celery result_expires = 86400s (24h)**: Results stored in Redis. Under load, this fills Redis memory. Should be reduced or use separate backend.

10. **No rate limiting on telemetry/ingest endpoint**: API key validate per request, but no per-car or per-org rate limiting.

---

## 9. MONITORING & OBSERVABILITY

### What's Instrumented
- `/metrics` endpoint with Prometheus (if prometheus-fastapi-instrumentator installed)
- Structured JSON logging (contextvars for request_id, user_id, org_id)
- Celery Flower monitoring at :5555

### What's NOT Monitored (Critical Gaps)
- **MQTT broker health**: No EMQX dashboard configured (port 8084 mapped but no auth)
- **Celery queue depth**: Not exposed as metric (Flower only shows current state)
- **Database connection pool usage**: Not exported
- **WebSocket connection count**: `get_active_connections_count()` not exposed
- **Telemetry ingestion rate**: No success/failure counter
- **Task execution latency**: No p99/avg processing time tracking
- **Redis memory usage**: Not tracked
- **API endpoint latency**: Prometheus instrumentation partially configured

---

## 10. EXTERNAL DEPENDENCIES & VERSIONS

| Dependency | Version | Purpose |
|-----------|---------|---------|
| FastAPI | 0.109.0 | Async web framework |
| SQLAlchemy | 2.0.25 | ORM with async support |
| asyncpg | 0.29.0 | Async PostgreSQL driver |
| gmqtt | 0.6.0 | Async MQTT client |
| redis-py | 5.0.1 | Async Redis client |
| Celery | 5.4.0 | Task queue |
| flower | 2.0.1 | Celery monitoring |
| python-jose | 3.3.0 | JWT handling |
| passlib | 1.7.4 | Password hashing (bcrypt) |
| numpy | (pinned) | Anomaly detection stats |
| httpx | 0.26.0 | Async HTTP for LLM calls |
| slowapi | 0.1.9 | Rate limiting (available but not used) |
| sentry-sdk | 1.40.0 | Error tracking (configured but not initialized in main.py) |
| prometheus-client | (transitive) | Metrics exposed |

---

## 11. Deployment Architecture (Production)

```
docker-compose.prod.yml:
├── postgres: timescale/timescaledb:latest-pg15 (2 CPU, 4GB RAM)
├── redis: redis:7-alpine (1 CPU, 1GB RAM)
├── backend: -fastapi container (2 CPU, 2GB RAM)
├── celery_worker: -a celery_app worker --concurrency=2
├── celery_beat: -a celery_app beat
├── flower: celery -A celery_app flower
├── mqtt: emqx/emqx:5.5.0
└── frontend: Next.js Dockerfile on :3000

Notes:
- No load balancer (no HA for backend)
- No database read replicas
- No MQTT cluster
- No Redis Sentinel/Cluster
- Single instance of everything
- Resources reserved but NO auto-scaling
- Backend, celery, flower all use same Dockerfile (bloated container)
```

---

## 12. SECURITY POSTURE

| Area | Status | Notes |
|------|--------|-------|
| Password Hashing | ✅ bcrypt (passlib) | Complexity rules in validation |
| JWT | ✅ HS256, 15min access + 7 day refresh | Token refresh with rotation + family detection |
| API Keys | ✅ SHA256 hashed, 256-bit random | No rotation, no usage quotas |
| Multi-tenant | ✅ Organization isolation on all queries | Car verification per org |
| CORS | ✅ Configurable | Production requires explicit origins |
| Rate Limiting | ⚠️ Partially | slowapi installed but NOT configured on endpoints |
| SQL Injection | ✅ SQLAlchemy ORM + parameterized queries | Raw SQL in daily aggregation only |
| Input Validation | ✅ Pydantic schemas on all endpoints | Strict type validation |
| Error Handling | ⚠️ Generic 500 fallback | Some endpoints leak stack traces in logs |
| Sentry | ⚠️ Configured but not initialized in main.py | Sentry SDK imported but no initialization call visible |
| LLM Circuit Breaker | ✅ 3 failures → 60s open | Fallback to canned DTC responses |

---

## SUMMARY: SYSTEM READINESS FOR 1000 USERS

```
                 ┌─────────────────────────────────────────┐
                 │           CURRENT CAPACITY               │
                 │                                         │
                 │  ├─ 50-100 cars (real-time 1Hz)         │
                 │  ├─ 50-100 concurrent WS users          │
                 │  ├─ ~20 Celery tasks/sec                │
                 │  ├─ ~500 DB writes/sec (peak)           │
                 │  └─ Single instance of all services     │
                 │                                         │
                 │           REQUIRED FOR 1000              │
                 │                                         │
                 │  ├─ 1000 cars (real-time 1Hz)          │
                 │  ├─ 1000 concurrent WS users            │
                 │  ├─ ~2000 Celery tasks/sec              │
                 │  ├─ ~1000 DB writes/sec (sustained)     │
                 │  └─ Horizontally scalable architecture  │
                 └─────────────────────────────────────────┘

                GAP FACTOR: ~20x-100x under current design
```

The current system is well-architected for a **proof-of-concept or small fleet (10-50 vehicles)**. For **1000 concurrent users with 1000 vehicles at 1Hz telemetry**, the following are REQUIRED:

1. **Batch telemetry ingestion** (not 1 task per message)
2. **Horizontal scaling** (multiple API instances, Celery workers, MQTT consumers)
3. **Database read replicas** + connection pooling tuning
4. **Asynchronous threshold checking in-process** (not Celery per ingest)
5. **WebSocket connection pooling / shared workers**
6. **Database partitioning strategy** (per-org, per-month)
7. **Message queuing buffering** (Kafka/RabbitMQ between MQTT and DB)
8. **Monitoring stack** (Grafana + Prometheus dashboards)
9. **Auto-scaling infrastructure** (Kubernetes or Docker Swarm)
10. **Load testing validation** before production deployment

**Current strength**: The architecture foundation (FastAPI async, MQTT pub/sub, Celery task queue, TimescaleDB time-series, Redis pub/sub) is correct and can scale with proper configuration and additional infrastructure.