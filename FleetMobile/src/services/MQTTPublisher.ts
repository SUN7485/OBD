/**
 * MQTT Publisher - Sends telemetry data to the API via HTTP
 * 
 * NOTE: The `mqtt` npm package is incompatible with React Native because it
 * depends on Node.js built-in modules (net, tls, stream, crypto, dns).
 * Instead, we use the existing HTTP API client to publish telemetry.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import api from './api';
import type { TelemetryData } from './OBDManager';

class MQTTPublisher {
  private connected: boolean = false;
  private carId: string = '';
  private offlineQueue: TelemetryData[] = [];
  private publishTimer: ReturnType<typeof setInterval> | null = null;

  setCarId(id: string): void {
    this.carId = id;
  }

  getCarId(): string {
    return this.carId;
  }

  private async loadOfflineQueue(): Promise<void> {
    try {
      const stored = await AsyncStorage.getItem('mqtt_offline_queue');
      if (stored) {
        this.offlineQueue = JSON.parse(stored);
      }
    } catch (e) {
      console.error('Failed to load offline queue:', e);
      this.offlineQueue = [];
    }
  }

  private async saveOfflineQueue(): Promise<void> {
    try {
      await AsyncStorage.setItem('mqtt_offline_queue', JSON.stringify(this.offlineQueue));
    } catch (e) {
      console.error('Failed to save offline queue:', e);
    }
  }

  async connect(): Promise<boolean> {
    await this.loadOfflineQueue();
    
    // "Connected" means we have a carId and can publish via HTTP
    if (this.carId) {
      this.connected = true;
      this.drainOfflineQueue();
      return true;
    }
    return false;
  }

  async publishTelemetry(data: TelemetryData): Promise<void> {
    if (this.connected && this.carId) {
      try {
        await api.ingestTelemetry({
          car_id: this.carId,
          speed: data.speed,
          rpm: data.rpm,
          coolant_temp: data.coolantTemp,
          engine_load: data.engineLoad,
          throttle: data.throttle,
          fuel_level: data.fuelLevel,
          latitude: data.latitude,
          longitude: data.longitude,
          timestamp: data.timestamp,
        });
      } catch (e) {
        console.log('Failed to publish telemetry, queuing offline');
        this.offlineQueue.push(data);
        await this.saveOfflineQueue();
      }
    } else {
      this.offlineQueue.push(data);
      await this.saveOfflineQueue();
      console.log('Queued telemetry offline, queue size:', this.offlineQueue.length);
    }
  }

  private async drainOfflineQueue(): Promise<void> {
    if (!this.connected || this.offlineQueue.length === 0) return;

    console.log(`Draining ${this.offlineQueue.length} offline telemetry records`);
    const batch = [...this.offlineQueue];
    this.offlineQueue = [];
    await this.saveOfflineQueue();

    for (const data of batch) {
      try {
        await api.ingestTelemetry({
          car_id: this.carId,
          speed: data.speed,
          rpm: data.rpm,
          coolant_temp: data.coolantTemp,
          engine_load: data.engineLoad,
          throttle: data.throttle,
          fuel_level: data.fuelLevel,
          latitude: data.latitude,
          longitude: data.longitude,
          timestamp: data.timestamp,
        });
      } catch {
        // Re-queue if still failing
        this.offlineQueue.push(data);
      }
    }
    await this.saveOfflineQueue();
  }

  async disconnect(): Promise<void> {
    if (this.publishTimer) {
      clearInterval(this.publishTimer);
      this.publishTimer = null;
    }
    this.connected = false;
  }

  isReady(): boolean {
    return this.connected;
  }

  getQueueSize(): number {
    return this.offlineQueue.length;
  }
}

export default new MQTTPublisher();