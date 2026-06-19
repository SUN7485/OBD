# FleetMobile - OBD-II BLE Telemetry Mobile App

React Native (Expo) mobile app for connecting ELM327 BLE OBD-II dongles to the Fleet OBD backend.

## Features

- **BLE Connection**: Scan and connect to ELM327 Bluetooth devices
- **Live Telemetry**: Real-time RPM, speed, coolant temp, engine load, fuel level
- **GPS Tracking**: Location data via expo-location
- **Authentication**: JWT token login/logout with expo-secure-store
- **MQTT Telemetry**: WebSocket MQTT publishing to `telemetry/{car_id}`
- **Real-time Alerts**: WebSocket alerts from `/api/v1/ws`
- **Offline Support**: Queue telemetry when disconnected

## Requirements

- Node.js 22+
- Expo CLI (`npm install -g expo-cli`)
- Physical device or emulator with Bluetooth support

## Setup

```bash
# Install dependencies
npm install

# Start development server
npm start
```

Then scan QR code with Expo Go app (Android) or use iOS Simulator.

## Configuration

Set environment variables in `.env`:

```
EXPO_PUBLIC_API_URL=http://localhost:8000
EXPO_PUBLIC_MQTT_HOST=localhost
```

For Android emulator, use `10.0.2.2` instead of `localhost`.

## Usage

1. **Login** with fleet credentials
2. **Scan** for OBD-II BLE devices
3. **Connect** to your vehicle's ELM327 adapter
4. **View** live telemetry on Gauges/Dashboard screens
5. **Receive** real-time alerts when issues are detected

## Build for Production

```bash
# Android
npx expo run:android

# iOS
npx expo run:ios
```

## Permissions

The app requires:
- BLUETOOTH_SCAN - for finding OBD devices
- BLUETOOTH_CONNECT - for connecting to devices
- ACCESS_FINE_LOCATION - for GPS and Android Bluetooth

## Project Structure

```
src/
  screens/          # App screens
    - LoginScreen.tsx
    - DashboardScreen.tsx
    - GaugesScreen.tsx
    - DiagnosticsScreen.tsx
    - AlertsScreen.tsx
    - SettingsScreen.tsx
    - BLEConnectScreen.tsx
  services/         # Core services
    - api.ts           # Backend API client
    - OBDManager.ts    # BLE communication
    - OBDService.ts    # PID parsing
    - MQTTPublisher.ts # MQTT WebSocket client
    - AlertWebSocket.ts # Real-time alerts
    - LocationService.ts # GPS
    - OfflineQueue.ts   # AsyncStorage queue
  store.ts          # Zustand state management
```

## Telemetry Flow

```
ELM327 (BLE) 
    ↓
OBDManager.readTelemetry()
    ↓
TelemetryStreamer (every 1-15s)
    ↓
MQTTPublisher.publishTelemetry()
    ↓
ws://localhost:8083/mqtt → topic: telemetry/{car_id}
    ↓
Backend (mqtt_client.py) → TimescaleDB
```