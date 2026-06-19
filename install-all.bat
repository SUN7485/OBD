@echo off
title Fleet OBD - Install All Dependencies
echo ========================================
echo Fleet OBD - Install All Dependencies
echo ========================================
echo.

echo [1/3] Installing Backend Python dependencies...
cd /d D:\obd\backend
if exist requirements.txt (
    pip install -r requirements.txt --upgrade
    if %ERRORLEVEL% equ 0 (
        echo Backend dependencies installed ✓
    ) else (
        echo WARNING: Some backend dependencies may have failed
    )
) else (
    echo ERROR: requirements.txt not found in backend folder
)

echo.
echo [2/3] Installing Frontend (Next.js)...
cd /d D:\obd\frontend
if exist package.json (
    call npm install
    if %ERRORLEVEL% equ 0 (
        echo Frontend dependencies installed ✓
    ) else (
        echo WARNING: Frontend npm install may have failed
    )
) else (
    echo ERROR: package.json not found in frontend folder
)

echo.
echo [3/3] Installing Mobile (React Native)...
set "MOBILE_DIR="
if exist D:\obd\mobile set "MOBILE_DIR=D:\obd\mobile"
if exist D:\obd\FleetMobile set "MOBILE_DIR=D:\obd\FleetMobile"

if defined MOBILE_DIR (
    cd /d %MOBILE_DIR%
    if exist package.json (
        call npm install
        if %ERRORLEVEL% equ 0 (
            echo Mobile dependencies installed ✓
        ) else (
            echo WARNING: Mobile npm install may have failed
        )
    ) else (
        echo ERROR: package.json not found in mobile folder
    )
) else (
    echo WARNING: No mobile folder found (mobile or FleetMobile)
    echo Create D:\obd\mobile and add package.json to enable mobile app
)

echo.
echo ========================================
echo All dependencies installed!
echo ========================================
echo.
echo Next steps:
echo   1. Install PostgreSQL (TimescaleDB) locally
echo   2. Install Redis locally, or use: docker run -d -p 6379:6379 redis:7-alpine
echo   3. Install EMQX MQTT or Mosquitto for telemetry:
echo      - EMQX: docker run -d -p 1883:1883 -p 8083:8083 emqx/emqx:5.5.0
echo      - Mosquitto: https://mosquitto.org/download/
echo   4. Run: start-all.bat
echo.
pause