# MQTT Telemetry Architecture Upgrade

## Goal
Replace HTTP telemetry ingest with MQTT for efficient IoT device communication and add TimescaleDB hypertables.

## Tasks

- [x] Add EMQX broker to docker-compose.yml → Verify: `docker-compose up mqtt` starts on port 1883
- [ ] Remove nested obd/obd/duplicate folder structure → Verify: Only D:\obd\backend, D:\obd\frontend, D:\obd\mobile exist
- [x] Create MQTT client service in backend → Verify: `backend/services/mqtt_client.py` can connect and subscribe
- [x] Add MQTT telemetry ingest endpoint → Verify: Publishing to `telemetry/{car_id}` stores data in DB
- [x] Add TimescaleDB hypertable migration → Verify: `obd_data` table is compressed, partitioned by time
- [x] Update React Native app to publish via MQTT → Verify: Mobile connects and publishes telemetry
- [ ] Verify Redis Pub/Sub in websocket_manager → Verify: Broadcast works across multiple instances

## Done When

- [x] MQTT broker runs in Docker (emqx/emqx:5.5.0 on port 1883)
- [x] Telemetry flows: Device → MQTT → TimescaleDB → WebSocket
- [ ] No nested duplicate folders
- [x] Hypertable compression configured (7-day policy for obd_data)

## Architecture Changes

```
ELM327 Device (BLE)
      ↓
React Native App
      ↓ MQTT (ws://localhost:8083)
EMQX Broker
      ↓
FastAPI Backend (mqtt_client.py subscriber)
      ↓              ↓
TimescaleDB       Redis Pub/Sub
                      ↓
                  WebSocket Manager
                      ↓
               Frontend + Mobile
```

## Files Modified/Created

1. `docker-compose.yml` - Added EMQX MQTT broker service
2. `.env.docker` - Added MQTT_URL configuration
3. `backend/services/mqtt_client.py` - New MQTT subscriber service
4. `backend/config/settings.py` - Added MQTT settings fields
5. `backend/requirements.txt` - Added gmqtt library
6. `backend/main.py` - Integrated MQTT into lifespan
7. `backend/alembic/versions/008_add_compression_policies.py` - Compression migration
8. `obd/FleetMobile/src/services/MQTTPublisher.ts` - Mobile MQTT publisher
9. `obd/FleetMobile/package.json` - Added react-native-mqtt dependency