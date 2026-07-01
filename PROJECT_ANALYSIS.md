# Fleet OBD Platform - Project Analysis Report

## Where You Are Now

You have built a **production-architecture fleet management platform** with three main components:
- **Backend**: FastAPI + Celery + TimescaleDB + Redis + EMQX (Python)
- **Frontend**: Next.js dashboard (TypeScript)
- **FleetMobile**: React Native/Expo mobile app (TypeScript)

The architecture is sound and feature-complete on paper. The data models are well-designed, the API surface is comprehensive, and the real-time pipeline (MQTT → WebSocket) is properly structured. However, there are **critical bugs** that will prevent the system from bordering correctly without fixes.

---

## Critical Failures (Will Break the System)

### 1. WebSocket Uses a Closed Database Session
**File**: `backend/api/v1/routes/websocket.py` (lines 136-138)
```python
async for db_session in get_db():
    db = db_session
    break
```

`get_db()` is an async generator that **closes the session after yielding**. The `break` triggers cleanup - `session.commit()` then `session.close()`. The WebSocket handler then uses this closed session for auth queries and car ID lookups. **Every WebSocket connection will fail on the first database operation.**

**Fix**: Replace with:
```python
async with session_manager() as db:
    # use db for entire connection lifetime
```

### 2. RLS Middleware Does Nothing
**File**: `backend/middleware/rls.py` (line 54-65)
```python
async def set_rls_session(org_id: str) -> None:
    # This is handled by the middleware which stores org_id in request state
    # The actual SQL session variable setting happens in the database connection
    pass
```

The function is a stub. Row-Level Security was disabled in migration 004. Multi-tenant data isolation relies entirely on application-level checks. If any endpoint forgets this filter, data leaks across organizations. **There is no DB-enforced tenant boundary.**

### 3. Next.js Frontend Never Refreshes Tokens
**File**: `frontend/src/lib/api.ts` (lines 24-34)

```javascript
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      if (typeof window !== 'undefined') {
        localStorage.removeItem('token')
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)
```

On 401, it immediately logs the user out. The access token expires after 15 minutes. **Users will be involuntarily logged out every 15 minutes.**

### 4. Duplicate Settings Fields
**File**: `backend/config/settings.py` (lines 21-23 and 29-31)

`MQTT_URL`, `MQTT_USERNAME`, `MQTT_PASSWORD` are defined twice. With `extra="ignore"`, Pydantic v2 silently ignores duplicates. The last definition wins, but this creates maintenance confusion.

---

## Likely Failures (Will Cause Issues in Production)

### 5. Celery Tasks Block the Event Loop
**File**: `backend/tasks/data_aggregator.py` and other task files

Tasks wrap async code with `asyncio.run(_aggregate_hourly())`. Celery workers are synchronous. `asyncio.run()` creates a new event loop per task invocation. With `worker_concurrency > 1`, this can cause:
- Event loop conflicts
- Blocked workers during blocking I/O
- Memory leaks from unclosed loops

### 6. Redis PubSub Subscribes Per-Connection
**File**: `backend/api/v1/routes/websocket.py` (lines 172-185)

Every WebSocket connection subscribes to `ws:user:{user.id}` on Redis. Redis PubSub creates a dedicated connection per subscription. With 1000 connected users = 1000 Redis connections. Redis has a default limit of 10,000 so it scales, but it's wasteful.

More critically: messages are published to `ws:org:{org_id}` but **only user-specific channels are subscribed**. If the Redis publish succeeds but no specific user channel is subscribed (because they connected without going through the WebSocket endpoint correctly), messages are lost.

### 7. FleetMobile API Client Has Wrong Parameter Names
**File**: `FleetMobile/src/services/api.ts`

- `getTelemetryHistory` sends `start_time`/`end_time` but backend expects `start`/`end` (datetime objects)
- `explainDTC` sends `{ code, car_id }` to `/ai/dtc-explain` but backend expects `{ car_id, dtc_codes: [] }`
- `getAlerts` default params `{}` will include `car_id: undefined` and `severity: undefined` as query params

### 8. Missing `.env.docker` File
**File referenced**: `docker-compose.yml` (line 4)

```yaml
env_file:
  - .env.docker
```

Docker Compose will fail to start. Only `.env`, `.env.example`, and `.env.prod` exist.

### 9. RLS Was Explicitly Disabled on the Most Critical Table
**File**: `backend/alembic/versions/004_add_compression.py`

TimescaleDB compression conflicts with PostgreSQL RLS. The migration explicitly disables RLS on `obd_data` (the hypertable). The time-series data has **no database-enforced row-level security**. All isolation depends on application-level filtering.

---

## What You Didn't Finish As Planned

### 10. No WebSocket Message for AI Replies
The WebSocket message format lists `ai_reply` as a server→client type, but the AI service creates `Message` records in the database and never broadcasts them via WebSocket. **AI chat replies won't appear in real-time.**

### 11. Rate Limiter Middleware Exists but Is Not Plugged In
**File**: `backend/middleware/rate_limiter.py`

The rate limiter exists but `main.py` doesn't include it in the middleware stack. No endpoint has rate limiting.

### 12. Batch Ingestion Router Registered But Missing
**File**: `backend/api/v1/routes/batch.py` - not in file listing.

The router is registered in `main.py` but wasn't found in the file tree. Either the endpoint exists but is untested, or it's referenced and doesn't exist.

### 13. Sentry Not Configured
`sentry-sdk[fastapi]` is in requirements.txt but no Sentry initialization code was found in `main.py`. Error tracking is silently skipped.

### 14. MQTT Reconnect Task Can Storm
**File**: `backend/services/mqtt_client.py` (line 39)

Multiple disconnects in rapid succession can create duplicate reconnect tasks.

### 15. Distance Calculation Is Wrong
**File**: `backend/tasks/data_aggregator.py` (lines 74-75)

```python
distance_km = avg_speed_kmh / 60  # 1 hour of driving at avg speed
```

This assumes constant speed for 1 hour. Real distance should be derived from GPS coordinates or OBD speed × actual time intervals. Fleet distance metrics will be inaccurate.

### 16. Mobile App Refresh Token Logic Has a Bug
**File**: `FleetMobile/src/services/api.ts` (line 147)

```typescript
const { data } = await this.client.post<LoginResponse>('/auth/refresh', {
  refresh_token: auth.refreshToken,
});
```

The backend expects `{ refresh_token: string }` and the mobile sends exactly that - but the backend's `/auth/refresh` endpoint actually expects the **old access token** to be rotated, not a raw refresh token. The backend's `rotate_refresh_token()` function accepts the raw refresh token string and looks it up in the DB, so this actually works. But the endpoint name and semantics are confusing.

---

## Security Concerns

| Issue | Severity | Location |
|-------|----------|----------|
| WebSocket uses closed DB session | **Critical** | `routes/websocket.py:136-138` |
| RLS not enforced at DB level | **High** | `middleware/rls.py`, `alembic/versions/004` |
| 15-min forced logout in dashboard | **High** | `frontend/src/lib/api.ts:24-34` |
| Celery `asyncio.run()` in workers | **High** | `tasks/data_aggregator.py` |
| No input range validation on OBD data | **Medium** | `schemas/telemetry.py` |
| MQTT topics not authenticated | **Medium** | `services/mqtt_client.py` |
| No retry budget on external calls | **Medium** | LLM client, MQTT, Redis operations |
| Password hashing uses default bcrypt cost | **Low** | `services/auth.py` - no explicit `rounds` parameter |

---

## How to Make This Better

### 1. Add Idempotency to Telemetry Ingestion
**Problem**: When devices reconnect after a network outage, they replay buffered telemetry. Without deduplication, you get duplicate records.

**Solution**: Add a unique constraint on `(car_id, time)` - it already exists (`uix_obd_data_time_car`). But MQTT messages might arrive with the same timestamp. Add an `idempotency_key` field to `TelemetryIngestRequest` and skip inserts where the key already exists. Even simpler: add a SHA256 hash of `(car_id, time, rpm, speed, ...)` as a dedup key and use `ON CONFLICT DO NOTHING`.

### 2. Add Circuit Breakers for External Dependencies
**Problem**: If Redis goes down, the MQTT client's reconnect loop will hammer Redis. If TimescaleDB is slow, Celery tasks queue up. A single slow dependency can cascade into a full outage.

**Solution**: Add a lightweight circuit breaker (even a simple state machine with `closed/open/half-open` states) around:
- Redis publish/subscribe
- LLM API calls
- Database writes in the ingestion pipeline

When the circuit is open, fast-fail with a cached/default response or queue for retry.

### 3. Implement Proper Data Retention
**Problem**: `obd_data` grows unbounded. At 1 message/second per car, 100 cars = 8.6M rows/day, 3.1B rows/year. TimescaleDB supports automatic data retention with continuous aggregates, but no policy is configured.

**Solution**: Configure TimescaleDB data retention:
```sql
SELECT add_retention_policy('obd_data', INTERVAL '90 days');
```
Keep `obd_data_hourly` for 2 years, `obd_data_daily` indefinitely. Move real-time queries to the raw table, historical queries to aggregates.

### 4. Add Correlation IDs for Observability
**Problem**: When debugging a telemetry message from ingestion through MQTT → WebSocket → frontend, there's no way to trace it. Each hop creates a new log entry with no linking identifier.

**Solution**: Add a `correlation_id` (UUID) to every telemetry record at ingestion. Pass it through:
- MQTT message metadata
- Celery task headers
- WebSocket message payload
- Frontend display

Use structured logging with the correlation ID as a field. This makes it possible to trace a single vehicle's data through the entire pipeline.

### 5. Fix the WebSocket Architecture
**Problem**: The current WebSocket design has two issues:
1. Closed DB session (critical bug)
2. Each connection creates a Redis PubSub subscription (resource waste)

**Solution**: 
- Fix the session bug first
- Reduce Redis subscriptions: instead of per-user subscriptions, publish all messages to `ws:globally` and have a single Redis listener per backend instance that distributes to local WebSocket connections. Cross-instance broadcasting still works via Redis.

### 6. Add Request/Response Validation Boundaries
**Problem**: The mobile app sends `start_time`/`end_time` as query params. The backend expects `start`/`end`. This mismatch means the API call silently fails or uses default values. There are no tests verifying the API contract between mobile and backend.

**Solution**: 
- Add Pydantic models for ALL query parameters (not just request bodies)
- Add OpenAPI schema tests that verify frontend/mobile API calls match the backend schema
- Generate TypeScript types from the OpenAPI spec (use `openapi-typescript` or `orval`)

### 7. Add Health Checks That Actually Verify Dependencies
**Problem**: `GET /health` probably returns 200 even if PostgreSQL is frozen or Redis is unreachable. The startup code in `main.py` verifies connections once at boot, but they can fail after.

**Solution**: Add a `/health/ready` endpoint that:
- Runs `SELECT 1` against PostgreSQL
- Runs `PING` against Redis
- Checks EMQX connection status
- Checks Celery worker availability
- Returns 503 if any dependency is unhealthy

### 8. Add a Graceful Shutdown Handler
**Problem**: When the backend container stops, it kills the process. WebSocket connections are dropped mid-message. Celery tasks are killed mid-execution. In-flight telemetry is lost.

**Solution**: Add signal handlers for SIGTERM/SIGINT:
1. Stop accepting new WebSocket connections
2. Wait for in-flight requests to complete (with timeout)
3. Flush pending MQTT messages to Redis
4. Tell Celery to finish current tasks and stop accepting new ones
5. Close database connections

### 9. Add Structured Logging
**Problem**: Current logging uses string interpolation:
```python
logger.info(f"Ingested telemetry for car {data.car_id} at {data.time}")
```
This is hard to parse and filter in production log aggregators.

**Solution**: Use structured logging:
```python
logger.info(
    "telemetry_ingested",
    extra={"car_id": str(data.car_id), "time": data.time.isoformat(), "org_id": str(org_id)}
)
```
Or use `structlog` which natively outputs JSON.

### 10. Add a Feature Flag System
**Problem**: Some features (AI chat, geofencing, maintenance predictions) are always "on" even if the underlying infrastructure (Ollama/LM Studio) isn't running. The AI service will throw errors on every call.

**Solution**: Add a simple feature flag system (even just a Redis-backed key-value store or database table). Check flags before invoking expensive/unavailable features:
```python
if not feature_flags.is_enabled("ai_chat", organization_id):
    raise HTTPException(503, "AI features not available")
```

### 11. Add Integration Tests for Critical Paths
**Problem**: Unit tests exist for individual services, but there are no tests verifying the end-to-end pipeline: MQTT → ingestion → WebSocket → frontend.

**Solution**: Add at minimum:
- Test that a published MQTT message appears in the database
- Test that ingesting telemetry triggers a WebSocket broadcast
- Test that a WebSocket connection receives telemetry for subscribed cars
- Test that auth token refresh works end-to-end

Use `pytest-asyncio` with a test database and a mock EMQX broker.

### 12. Add a Migration/Deployment Safety Net
**Problem**: The current setup has no database migration rollback strategy. If `alembic upgrade head` fails halfway through, the database is in an inconsistent state.

**Solution**: 
- Always wrap `alembic upgrade` in a transaction where possible
- Add `downgrade` functions to all migrations
- Add a pre-deployment health check that verifies the database schema version matches the code expects
- Test migrations on a copy of production data before deploying

### 13. Add Rate Limiting Per-Endpoint With Different Budgets
**Problem**: Either no rate limiting (current) or all-or-nothing.

**Solution**: Apply different limits:
- Auth endpoints: 5 requests/minute (brute force protection)
- Telemetry ingestion: 1000 requests/minute per device (high throughput)
- AI endpoints: 10 requests/minute per user (expensive LLM calls)
- WebSocket connections: 5/minute per IP (prevent connection floods)

### 14. Separate Development and Production Dockerfiles
**Problem**: The current `Dockerfile` uses `uvicorn --reload` which is development mode. The production `docker-compose.prod.yml` probably uses the same image.

**Solution**: Add a `Dockerfile.prod`:
- No `--reload` flag
- Multi-stage build (build dependencies in one stage, copy only runtime artifacts)
- Run as non-root user
- Use `gunicorn` or `uvicorn` with multiple workers

### 15. Add a Webhook Retry Queue
**Problem**: Webhooks are fired and forgotten. If the target URL is down, the webhook is lost. The `WebhookConfiguration` model tracks `failure_count` but there's no retry mechanism.

**Solution**: Add a `webhook_deliveries` table with status (`pending`, `sent`, `failed`, `exhausted`). A Celery task retries failed deliveries with exponential backoff. After N attempts, mark as exhausted and alert the user.

---

## Architecture Strengths

- Solid microservice separation with clear domain boundaries
- Comprehensive data model with proper relationships and indexes
- Proper async/await throughout the Python backend
- Good separation of concerns (routes → services → domain models)
- Real-time architecture is well-planned (MQTT for device ingestion, WebSocket for browser updates)
- Monitoring infrastructure (Prometheus, Flower, health checks) is in place
- Multi-tenant design with organization isolation pattern

## Architecture Weaknesses

- **Defense in depth is missing** - RLS was designed but disabled; application checks are the only protection
- **No circuit breakers** - If Redis goes down, MQTT reconnection storms can cascade
- **No idempotency** - Telemetry ingestion has no deduplication; reconnects can replay data
- **Distance calculation is wrong** - `avg_speed_kmh / 60` assumes constant speed for 1 hour
- **No data retention policy** - OBDData grows unbounded; no automatic cleanup configured
- **No graceful shutdown** - Connections are killed abruptly; in-flight data is lost
- **No correlation IDs** - Can't trace a single telemetry message through the pipeline