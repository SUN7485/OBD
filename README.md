# Fleet OBD Platform

A production-ready vehicle fleet management and telemetry platform with OBD-II data ingestion, real-time WebSocket communication, and AI-powered diagnostics.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Monorepo Structure                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────┐     ┌─────────────────┐               │
│  │  React Native   │────▶│  EMQX Broker    │               │
│  │  Mobile App     │     │  (MQTT/WebSocket)│               │
│  └────────┬────────┘     └────────┬────────┘               │
│           │                     │                           │
│           │              ┌──────▼──────┐                  │
│           │              │             │                  │
│      ┌────▼────┐   ┌─────▼─────┐  ┌────▼────┐              │
│      │  BLE    │   │ FastAPI   │  │ Redis   │              │
│      │ OBD-II  │   │ :8000    │  │ :6379  │              │
│      └────────┘   └─────┬─────┘  └────────┘              │
│                        │                                 │
│                 ┌─────┴─────┐                           │
│                 │           │                           │
│            TimescaleDB      Celery                       │
│             :5432         Workers                      │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### Components

- **frontend/** - Next.js dashboard (Vercel-deployable)
- **backend/** - FastAPI application with async endpoints
- **backend/tasks/** - Celery workers for background processing
- **docker-compose.yml** - Development services (Redis, TimescaleDB, EMQX, backend, frontend)
- **docker-compose.prod.yml** - Production stack for VPS deployment

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Node.js 20+
- Python 3.11+

### Run Locally with Docker

```bash
# Copy environment template
cp .env.example .env.docker

# Edit .env.docker with your preferred values
# IMPORTANT: Generate a secure JWT_SECRET
# openssl rand -hex 32

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend
```

Services:
- Backend: http://localhost:8000
- Frontend: http://localhost:3000
- PostgreSQL: localhost:5433
- Redis: localhost:6380
- EMQX: localhost:1883 (MQTT), 8083 (WebSocket)
- Flower (Celery): http://localhost:5555

### Frontend Development

```bash
cd frontend
npm install
npm run dev
```

### Backend Development

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

## Deployment

### Dashboard (Vercel)

The Next.js dashboard deploys to Vercel as a serverless function. It connects to the backend via API calls and WebSocket connections.

**Deploy steps:**
1. Push code to GitHub
2. In Vercel dashboard: Create project → Connect repository
3. Set **Root Directory** to `frontend`
4. Configure environment variables:
   - `NEXT_PUBLIC_API_URL` - Your production backend URL (e.g., `https://api.yourdomain.com`)
   - `NEXT_PUBLIC_WS_URL` - Your production WebSocket URL (e.g., `wss://api.yourdomain.com`)
   - `NEXT_PUBLIC_MAPBOX_TOKEN` - Mapbox token for maps (optional)
5. Deploy

**Why Vercel for frontend only:**
- Static generation and CDN for fast global delivery
- Edge network for low-latency UI responses
- Serverless functions work well for API routes and SSR

### Backend Stack (VPS with Docker)

The backend stack deploys via `docker-compose.prod.yml` on a VPS. This includes:

- **FastAPI** - Web API server (workers for production)
- **Celery** - Background task processing (beat + workers)
- **Redis** - Cache and message broker
- **TimescaleDB** - Time-series database
- **EMQX** - MQTT/WebSocket broker

**Deploy steps:**
1. Copy `.env.example` to `.env.prod` and configure:
   - `DATABASE_URL` - Production database connection
   - `REDIS_URL` - Production Redis connection
   - `JWT_SECRET` - Generate with `openssl rand -hex 32`
   - `CORS_ORIGINS` - Your production frontend URL(s)
   - Set `ENVIRONMENT=prod`
2. SSH to your VPS and clone the repository
3. Copy `.env.prod` to `.env` on the server
4. Run:
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```
5. Set up reverse proxy (nginx included for HTTP routing)

**Why VPS (not Vercel) for backend:**
- **Long-running processes**: Celery beat and workers need persistent background processes, incompatible with serverless
- **WebSocket connections**: Real-time telemetry requires persistent connections that serverless platforms can't maintain
- **MQTT broker**: EMQX is a stateful message broker requiring always-on presence
- **TimescaleDB persistence**: Database needs persistent storage with specific performance requirements
- **Redis**: Background task queue and caching require persistent in-memory storage

## Environment Variables

### Backend Required Variables

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection URL |
| `JWT_SECRET` | Secret key for JWT signing (generate with `openssl rand -hex 32`) |

### Frontend Required Variables (Vercel)

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_API_URL` | Backend API URL |
| `NEXT_PUBLIC_WS_URL` | WebSocket URL for real-time updates |
| `NEXT_PUBLIC_MAPBOX_TOKEN` | Mapbox token (optional) |

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /api/v1/auth/login` | Login |
| `POST /api/v1/auth/register` | Register |
| `GET /api/v1/auth/me` | Current user |
| `POST /api/v1/telemetry/ingest` | Ingest telemetry |
| `GET /api/v1/telemetry/history` | Query history |
| `WS /api/v1/ws` | WebSocket |
| `GET /api/v1/health` | Health check |
| `GET /metrics` | Prometheus metrics |

## License

MIT