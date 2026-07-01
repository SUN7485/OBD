# Implementation Plan

[Overview]
Fix all remaining critical, high-priority, and medium-priority issues in the Fleet OBD Platform to make the system production-ready and resilient against common failure modes.

This plan addresses the remaining gaps identified in PROJECT_ANALYSIS.md: RLS enforcement, Celery async issues, MQTT reconnect storms, incorrect distance calculations, missing idempotency, no circuit breakers, dummy batch endpoint, unstructured logging, no correlation IDs, and incomplete graceful shutdown.

[Types]
Add new types for correlation tracking, circuit breaker state, idempotency keys, and structured logging context.

- `CorrelationContext` (dataclass): correlation_id, car_id, organization_id, user_id, message_type, timestamp
- `CircuitBreakerState` (enum): CLOSED, OPEN, HALF_OPEN
- `CircuitBreaker` (dataclass): state, failure_count, last_failure_time, threshold, recovery_timeout
- `IdempotencyKey` (str): SHA256 hash of (car_id, time, rpm, speed, throttle, fuel_level, latitude, longitude)
- `StructuredLogContext` (dict): correlation_id, car_id, org_id, user_id, duration_ms, status

[Files]
Modify existing files and create new utility modules for cross-cutting concerns.

New files:
- `backend/utils/circuit_breaker.py` - Circuit breaker implementation
- `backend/utils/correlation.py` - Correlation ID management and context propagation
- `backend/utils/structured_logging.py` - Structured logging setup with JSON output
- `backend/middleware/circuit_breaker_middleware.py` - FastAPI middleware for circuit breaking external calls

Modified files:
- `backend/middleware/rls.py` - Implement actual RLS session variable setting
- `backend/services/mqtt_client.py` - Fix reconnect task lifecycle
- `backend/tasks/data_aggregator.py` - Fix asyncio.run pattern and distance calculation
- `backend/services/telemetry.py` - Add idempotency key generation and dedup logic
- `backend/api/v1/routes/batch.py` - Implement real batch ingestion with idempotency
- `backend/main.py` - Add structured logging, correlation ID middleware, graceful shutdown improvements
- `backend/services/redis_client.py` - Add circuit breaker around Redis operations
- `backend/services/llm_client.py` - Add circuit breaker around LLM calls
- `backend/api/v1/routes/telemetry.py` - Add correlation ID and idempotency check to ingestion
- `backend/alembic/versions/` - Add migration for idempotency_key column on obd_data
- `backend/domain/models.py` - Add idempotency_key field to OBDData model
- `backend/services/websocket_manager.py` - Include correlation_id in broadcast messages

[Functions]
New and modified functions for resilience and observability.

New functions:
- `circuit_breaker.py`: `CircuitBreaker.__init__`, `CircuitBreaker.can_execute`, `CircuitBreaker.record_success`, `CircuitBreaker.record_failure`, `CircuitBreaker.get_state`
- `correlation.py`: `generate_correlation_id`, `get_correlation_id`, `set_correlation_id`, `CorrelationMiddleware`
- `structured_logging.py`: `setup_structured_logging`, `log_with_context`
- `rls.py`: `set_rls_session` (replace stub with actual implementation)

Modified functions:
- `mqtt_client.py`: `_on_disconnect` - properly cancel old reconnect task before creating new one
- `data_aggregator.py`: `aggregate_hourly_data` - replace `asyncio.run()` with proper async execution; fix distance calculation
- `telemetry.py`: `ingest_telemetry` - generate idempotency key, check for duplicates before insert
- `batch.py`: `batch_process` - implement real batch ingestion with idempotency
- `main.py`: `lifespan` - add graceful shutdown with signal handlers
- `redis_client.py`: `publish`, `subscribe`, `get`, `set` - wrap with circuit breaker
- `websocket_manager.py`: `broadcast_to_room`, `broadcast_to_car`, `broadcast_to_org` - include correlation_id in messages

[Classes]
New classes for circuit breaking and correlation tracking.

- `CircuitBreaker` in `utils/circuit_breaker.py`: Generic circuit breaker with state management, failure threshold, recovery timeout
- `CorrelationMiddleware` in `utils/correlation.py`: FastAPI middleware that generates/propagates correlation IDs via request state and headers
- `JSONFormatter` in `utils/structured_logging.py`: Python logging formatter that outputs JSON with standard fields

Modified classes:
- `MQTTClientWrapper` in `services/mqtt_client.py`: Fix reconnect task management
- `OBDData` in `domain/models.py`: Add `idempotency_key` column with unique constraint

[Dependencies]
No new external packages required. Use stdlib and existing packages.

- Use `hashlib` for idempotency key generation (already available)
- Use `logging` with custom `Formatter` for structured logging (already available)
- Use `signal` for graceful shutdown (already available)
- Use `asyncio` task cancellation patterns (already available)

[Testing]
Add/update tests for new functionality.

- `tests/test_circuit_breaker.py` - Test circuit breaker state transitions
- `tests/test_idempotency.py` - Test duplicate telemetry rejection
- `tests/test_correlation.py` - Test correlation ID propagation
- `tests/test_rls.py` - Test RLS session variable setting
- Update `tests/test_telemetry_service.py` - Test idempotency in ingestion
- Update `tests/test_mqtt_client.py` - Test reconnect task management

[Implementation Order]
Sequential order to minimize conflicts and ensure each layer builds on the previous.

1. Add idempotency_key column to OBDData model and generate migration
2. Implement circuit breaker utility
3. Implement correlation ID middleware and utilities
4. Implement structured logging setup
5. Fix RLS middleware stub with actual session variable setting
6. Fix MQTT reconnect task lifecycle
7. Fix Celery data_aggregator asyncio.run pattern and distance calculation
8. Add idempotency to telemetry ingestion service
9. Implement real batch ingestion endpoint
10. Add circuit breakers to Redis client and LLM client
11. Wire structured logging, correlation middleware, and graceful shutdown into main.py
12. Update WebSocket manager to include correlation_id in broadcasts
13. Add comprehensive tests
14. Run full test suite and fix any regressions