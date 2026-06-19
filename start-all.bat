@echo off
title Fleet OBD - Local Launcher
echo ========================================
echo Fleet OBD - Starting Local Services
echo ========================================
echo.

echo Checking for required services...
echo.

REM Check PostgreSQL
echo [Checking] PostgreSQL on port 5432...
netstat -an 2>nul | findstr ":5432" >nul
if %ERRORLEVEL% equ 0 (
    echo   PostgreSQL: RUNNING
) else (
    echo   PostgreSQL: NOT RUNNING
    echo   Install TimescaleDB or start with Docker:
    echo     docker run -d --name timescaledb -p 5432:5432 -e POSTGRES_PASSWORD=password123 timescale/timescaledb:latest-pg15
)

REM Check Redis
echo [Checking] Redis on port 6379...
netstat -an 2>nul | findstr ":6379" >nul
if %ERRORLEVEL% equ 0 (
    echo   Redis: RUNNING
) else (
    echo   Redis: NOT RUNNING
    echo   Start Redis: docker run -d --name redis -p 6379:6379 redis:7-alpine
)

REM Check MQTT
echo [Checking] MQTT on port 1883...
netstat -an 2>nul | findstr ":1883" >nul
if %ERRORLEVEL% equ 0 (
    echo   MQTT: RUNNING
) else (
    echo   MQTT: NOT RUNNING
    echo   Start EMQX: docker run -d --name emqx -p 1883:1883 -p 8083:8083 emqx/emqx:5.5.0
    echo   Or install Mosquitto: https://mosquitto.org/download/
)

echo.
echo ========================================
echo Starting services...
echo ========================================
echo.

echo [Starting] Backend (FastAPI)...
start "Fleet API (Backend)" cmd /k "cd /d D:\obd && uvicorn backend.main:app --reload --port 8000"

timeout /t 2 /nobreak >nul

echo [Starting] Frontend (Next.js)...
start "Fleet Dashboard (Frontend)" cmd /k "cd /d D:\obd\frontend && npm run dev"

echo.
echo ========================================
echo Services launched!
echo ========================================
echo.
echo URLs:
echo   Dashboard:  http://localhost:3000
echo   API Docs:   http://localhost:8000/docs
echo   API Health: http://localhost:8000/api/v1/health
echo   MQTT Port:  ws://localhost:8083/mqtt (if EMQX running)
echo   Redis:      localhost:6379
echo.
echo To start Celery worker (for async tasks):
echo   start "Celery Worker" cmd /k "cd /d D:\obd && celery -A backend.celery_app worker --loglevel=info --pool=solo"
echo.
echo You can safely close THIS window now.
pause