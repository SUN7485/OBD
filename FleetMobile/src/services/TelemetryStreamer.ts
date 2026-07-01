/**
 * Telemetry Streamer - MQTT-based telemetry streaming with offline fallback
 */

import NetInfo, { NetInfoState } from '@react-native-community/netinfo';
import OBDManager, { TelemetryData } from './OBDManager';
import MQTTPublisher from './MQTTPublisher';
import OfflineQueue, { type QueuedTelemetry } from './OfflineQueue';
import LocationService from './LocationService';
import { useOBDStore } from '../store';

const INTERVAL_WIFI = 1000;
const INTERVAL_CELLULAR = 5000;
const INTERVAL_OFFLINE = 10000;

class TelemetryStreamer {
  private interval: number = INTERVAL_OFFLINE;
  private timer: ReturnType<typeof setInterval> | null = null;
  private carId: string = '';
  private isRunning: boolean = false;
  private netInfoListener: (() => void) | null = null;

  constructor() {
  }

  private setupNetworkListener(): void {
    if (this.netInfoListener) return;
    this.netInfoListener = NetInfo.addEventListener(this.handleNetChange.bind(this));
  }

  private handleNetChange(state: NetInfoState): void {
    if (state.type === 'wifi') {
      this.interval = INTERVAL_WIFI;
      console.log('Network: WiFi - using 1s telemetry interval');
    } else if (state.type === 'cellular' && state.isConnected) {
      this.interval = INTERVAL_CELLULAR;
      console.log('Network: Cellular - using 5s telemetry interval');
    } else {
      this.interval = INTERVAL_OFFLINE;
      console.log('Network: Offline - using 10s interval');
    }

    if (this.isRunning) {
      this.restartPolling();
    }
  }

  setCarId(id: string): void {
    this.carId = id;
    MQTTPublisher.setCarId(id);
  }

  async start(): Promise<void> {
    if (this.isRunning) return;

    this.setupNetworkListener();
    this.isRunning = true;
    OfflineQueue.load();
    this.startPolling();
    LocationService.startTracking((loc) => {
      console.log('Location update:', loc);
    });
    this.drainOfflineQueue();
  }

  stop(): void {
    this.isRunning = false;
    this.stopPolling();
    LocationService.stopTracking();
    MQTTPublisher.disconnect();
  }

  private startPolling(): void {
    this.stopPolling();

    this.timer = setInterval(async () => {
      await this.uploadCurrentTelemetry();
    }, this.interval);
  }

  private stopPolling(): void {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }
  }

  private restartPolling(): void {
    if (this.isRunning) {
      this.startPolling();
    }
  }

  private async uploadCurrentTelemetry(): Promise<void> {
    const obdData = await OBDManager.readTelemetry();
    const location = await LocationService.getCurrentLocation();

    const payload: TelemetryData = {
      ...obdData,
      latitude: location?.latitude,
      longitude: location?.longitude,
    };

    useOBDStore.getState().updateTelemetry(obdData);

    if (MQTTPublisher.isReady()) {
      MQTTPublisher.publishTelemetry(payload);
    } else {
      OfflineQueue.enqueue({
        car_id: this.carId,
        speed: obdData.speed,
        rpm: obdData.rpm,
        coolantTemp: obdData.coolantTemp,
        engineLoad: obdData.engineLoad,
        throttle: obdData.throttle,
        fuelLevel: obdData.fuelLevel,
        intakeAirTemp: obdData.intakeAirTemp,
        mafAirFlow: obdData.mafAirFlow,
        dtcCodes: obdData.dtcCodes,
        timestamp: new Date().toISOString(),
      } as QueuedTelemetry);
      this.drainOfflineQueue();
    }
  }

  private async drainOfflineQueue(): Promise<void> {
    const queued = await OfflineQueue.getAll();
    if (queued.length === 0) return;

    console.log(`Processing ${queued.length} offline telemetry records...`);

    for (const payload of queued) {
      if (!MQTTPublisher.isReady()) break;
      try {
        MQTTPublisher.publishTelemetry(payload as TelemetryData);
        await OfflineQueue.dequeue();
      } catch (error) {
        console.error('Failed to process queued telemetry:', error);
        break;
      }
    }
  }

  getInterval(): number {
    return this.interval;
  }

  isActive(): boolean {
    return this.isRunning;
  }

  destroy(): void {
    this.stop();
    if (this.netInfoListener) {
      this.netInfoListener();
    }
  }
}

export default new TelemetryStreamer();