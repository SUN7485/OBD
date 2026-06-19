# Fleet OBD Architecture

## Overview

Fleet OBD is a full-stack vehicle fleet management platform consisting of:
- **FastAPI Backend**: REST API + WebSocket server
- **Next.js Dashboard**: React-based web UI
- **React Native Mobile**: Cross-platform mobile app

## Technology Stack

| Layer | Technology |
|-------|-------------|
| Backend | FastAPI, Python 3.11 |
| Database | TimescaleDB (PostgreSQL) |
| Cache/Queue | Redis 7 |
| Message Broker | EMQX MQTT 5.5 |
| Task Queue | Celery |
| Frontend | Next.js 14, Ant Design |
| Mobile | React Native 0.84 |
| AI | LM Studio (local LLM) |

## System Architecture

```
                    ┌─────────────────┐
                    │   LM Studio     │
                    │   (Local LLM)   │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  FastAPI        │
                    │  Backend       │
                    │  :8000          │
                    └────────┬────────┘
                             │
          ┌────────────────────┼────────────────────┐
          │                  │                    │
     ┌────▼────┐       ┌─────▼─────┐      ┌────────▼────────┐
     │Timescale│       │   Redis   │      │  EMQX MQTT      │
     │   DB    │       │  Cache   │      │  :1883/:8083    │
     │ :5432   │       │  :6379   │      └────────────────┘
     └─────────┘       └──────────┘              │
                                               │
                                        ┌──────▼──────┐
                                        │ Mobile App  │
                                        │ (BLE OBD)   │
                                        └─────────────┘
```

### Telemetry Flow (MQTT)

```
ELM327 Device (BLE)
      ↓
React Native Mobile
      ↓ MQTT (QoS 1)
EMQX Broker
      ↓
FastAPI MQTT Subscriber → TimescaleDB
      ↓
Redis Pub/Sub → WebSocket Manager
      ↓
Dashboard + Mobile Real-time Updates
```

## Data Models

### Core Entities

- **Organization**: Multi-tenant organization
- **User**: Organization members with roles (admin, driver)
- **Car**: Vehicle with OBD-II connection
- **Telemetry**: Time-series OBD data
- **Alert**: Threshold-based alerts
- **Geofence**: Location boundaries

### Authentication

- **JWT**: Access tokens (15 min) + Refresh tokens (7 days)
- **API Keys**: Device-level telemetry authentication
- **API Key Rotation**: Automatic refresh token rotation

## API Design

### REST Endpoints

```
/api/v1/auth/
  POST /login
  POST /register
  POST /refresh
  POST /logout

/api/v1/telemetry/
  POST /ingest
  GET /history
  GET /live/{car_id}

/api/v1/fleet/
  /cars
  /geofences
  /drivers
  /maintenance

/api/v1/alerts/
  GET /
  PATCH /{id}/read
  PATCH /{id}/resolve

/api/v1/ai/
  POST /chat
  POST /dtc-explain
```

### WebSocket

```
WS /api/v1/ws?token=<jwt>
```

Events:
- `telemetry`: Real-time vehicle data
- `alert`: Threshold breach alerts
- `geofence`: Geofence events

## Security

- **CORS**: Configurable origins (required in prod)
- **Rate Limiting**: Redis-backed rate limiter
- **API Keys**: Device-level auth for telemetry
- **Password**: bcrypt hashing with complexity rules
- **Tokens**: JWT with HS256

## Deployment

### Development

```bash
docker-compose up
```

### Production

```bash
docker-compose -f docker-compose.prod.yml up
```

Resources:
- Backend: 2 CPU, 2GB RAM
- Database: 2 CPU, 4GB RAM
- Redis: 1 CPU, 1GB RAM

## Mobile Architecture

```
┌─────────────────┐      ┌─────────────────┐
│  BLE Manager    │────▶│  OBD Manager   │
│ (react-native-  │      │  (ELM327)       │
│  ble-plx)       │      └────────┬────────┘
└───────┬─────────┘               │
        │                         │
        ▼                         ▼
┌─────────────────┐      ┌─────────────────┐
│ Telemetry       │────▶│  MQTT Publisher │
│ Streamer        │      │  (QoS 1)        │
└─────────────────┘      └────────┬────────┘
                                  │
                                  ▼
                          ┌─────────────────┐
                          │  EMQX Broker    │
                          │  telemetry/{id}  │
                          └─────────────────┘
```

## Telemetry Intervals

| Network | Interval |
|---------|----------|
| WiFi | 1 second |
| Cellular | 15 seconds |
| Offline | 30 seconds |

## Future Considerations

- Real-time trip detection
- Driver behavior scoring
- Predictive maintenance
- Webhook integrations
- Multi-org support