# Reliability and 1000-User Scale Plan

## Goal
Fix critical reliability gaps and scale the system to 1000 concurrent vehicles with sustained 1Hz telemetry.

## Tasks
- [x] **Remove duplicate `MQTT_URL`/username/password fields from `backend/config/settings.py`** → Verify: `pydantic-settings` no longer warns about field overwrite
- [x] **Add batch telemetry ingestion in `services/telemetry.py` and `api/v1/routes/telemetry.py`** (buffer 10-50 readings per commit) → Verify: `POST /api/v1/telemetry/ingest/batch` accepts up to 50 items
- [x] **Replace per-task `asyncio.run()` DB sessions in all `backend/tasks/*.py` with shared engine/connection pooling** → Verify: Celery load test shows connection pool stays under max_overflow
- [x] **Enable slowapi rate limiting on telemetry endpoints** → Verify: Rate limit middleware integrated, `/metrics` shows limiter state
- [x] **Add MQTT message deduplication (message_id cache + idempotent upsert)** → Verify: Unique constraint `uix_obd_data_source_msg` added
- [x] **Tune TimescaleDB: compression after 7 days, refresh policy, and hypertable chunk interval to 1 hour** → Verify: Migration 009 created
- [x] **Add `/metrics` basic auth and expose WS/celery/queue gauges to Prometheus** → Verify: `/metrics` requires admin role
- [x] **Add API key rotation endpoint + usage quota enforcement** → Verify: `POST /api/v1/fleet/api-keys/{id}/rotate` returns new key
- [x] **Add startup validations for required env vars and fail-fast on missing config** → Verify: App crashes with clear message when required vars missing in prod in `backend/config/settings.py`

## Done When
- [ ] `docker compose -f docker-compose.prod.yml up` starts without warnings
- [ ] Load test script hits 1000 ingests/sec for 60 seconds with 0% error rate
- [ ] Prometheus dashboard shows queue depth, DB pool usage, and WS connection count

## Summary of Changes
1. `backend/config/settings.py`: Removed duplicates, added prod validators, rate limit fields
2. `backend/services/telemetry.py`: Fixed `ingest_mqtt_reading`, added `ingest_telemetry_batch`
3. `backend/domain/models.py`: Added `source_message_id` unique constraint
4. `backend/middleware/rate_limiter.py`: Cleaned up, integrated with main.py
5. `backend/main.py`: Added SlowAPI middleware, secured Prometheus metrics
6. `backend/api/v1/routes/health.py`: Protected `/metrics` endpoint for admin only
7. `backend/api/v1/routes/fleet.py`: Added `/api-keys/{id}/rotate` and `/api-keys/{id}/usage`
8. `backend/services/api_keys.py`: Added `rotate_api_key` and `get_api_key_usage`
9. `backend/alembic/versions/009_tune_timescale_for_scale.py`: Timescale tuning migration