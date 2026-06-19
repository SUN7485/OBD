/**
 * Telemetry Streamer - MQTT-based telemetry streaming with offline fallback
 */

import NetInfo, { NetInfoState } from '@react-native-community/netinfo';
import OBDManager, { TelemetryData } from './OBDManager';
import MQTTPublisher from './MQTTPublisher';
import OfflineQueue from './OfflineQueue';
import LocationService from './LocationService';

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
    this.setupNetworkListener();
  }

  private setupNetworkListener(): void {
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

    this.isRunning = true;
    await OfflineQueue.load();
    await this.drainOfflineQueue();
    this.startPolling();
    LocationService.startTracking((loc) => {
      console.log('Location update:', loc);
    });
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

    if (MQTTPublisher.isReady()) {
      MQTTPublisher.publishTelemetry(payload);
    } else {
      OfflineQueue.enqueue({
        ...payload,
        car_id: this.carId,
        timestamp: new Date().toISOString(),
      });
      await this.drainOfflineQueue();
    }
  }

  private async drainOfflineQueue(): Promise<void> {
    const queued = await OfflineQueue.getAll();
    if (queued.length === 0) return;

    console.log(`Processing ${queued.length} offline telemetry records...`);

    for (const payload of queued) {
      try {
        if (MQTTPublisher.isReady()) {
          MQTTPublisher.publishTelemetry(payload as TelemetryData);
          await OfflineQueue.dequeue();
        }
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