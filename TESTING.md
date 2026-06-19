# Fleet OBD Testing Guide

## Prerequisites
- Docker Desktop running
- Node.js 20+
- Python 3.11+

---

## 1. Backend Tests

```cmd
cd D:\obd\backend
pip install -r requirements.txt
pytest tests/ -v
```

---

## 2. Start Development Environment (Docker)

```cmd
cd D:\obd
docker-compose up -d
```

Check status:
```cmd
docker-compose ps
```

View logs:
```cmd
docker-compose logs -f backend
```

---

## 3. Backend Health Check

```cmd
curl http://localhost:8000/api/v1/health/
curl http://localhost:8000/api/v1/health/live
curl http://localhost:8000/api/v1/health/ready
curl http://localhost:8000/metrics
```

---

## 4. Test API Auth Flow

Register:
```cmd
curl -X POST http://localhost:8000/api/v1/auth/register ^
  -H "Content-Type: application/json" ^
  -d "{\"email\":\"test@example.com\",\"password\":\"Test1234!\",\"full_name\":\"Test User\",\"organization_name\":\"Test Org\"}"
```

Login:
```cmd
curl -X POST http://localhost:8000/api/v1/auth/login ^
  -H "Content-Type: application/json" ^
  -d "{\"email\":\"test@example.com\",\"password\":\"Test1234!\"}"
```

---

## 5. Frontend Tests

```cmd
cd D:\obd\frontend
npm install
npm run lint
npm run build
```

Start dev server:
```cmd
npm run dev
```

---

## 6. Production Build (Docker)

```cmd
cd D:\obd
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d
```

---

## 7. Mobile App

Install dependencies:
```cmd
cd D:\obd\FleetMobile
npm install
```

Lint:
```cmd
npm run lint
```

Run tests:
```cmd
npm test
```

Build debug APK:
```cmd
cd android
.\gradlew assembleDebug
```

The APK will be at: `android\app\build\outputs\apk\debug\app-debug.apk`

---

## 8. Database Operations

Run migrations:
```cmd
cd D:\obd\backend
alembic upgrade head
```

Create seed data:
```cmd
cd D:\obd
python scripts/seed_demo.py
```

Backup database:
```cmd
cd D:\obd\scripts
.\backup.sh
```

---

## 9. Flower (Celery Monitor)

```cmd
curl http://localhost:5555
```

---

## 10. Verify All Services

```cmd
docker-compose ps
```

Expected:
| Service | Status | Port |
|---------|--------|------|
| postgres | Up | 5432 |
| redis | Up | 6379 |
| backend | Up | 8000 |
| celery_worker | Up | - |
| celery_beat | Up | - |
| flower | Up | 5555 |
| frontend | Up | 3000 |

---

## Quick Full Test Sequence

```cmd
cd D:\obd\backend && pytest tests/ -v
cd D:\obd && docker-compose up -d
curl http://localhost:8000/api/v1/health/
curl http://localhost:3000
cd D:\obd\FleetMobile && npm test
```

---

## 11. Frontend E2E Tests (Playwright)

```cmd
cd D:\obd\frontend
npx playwright install
npx playwright test
```

Requires backend running at http://localhost:8000
