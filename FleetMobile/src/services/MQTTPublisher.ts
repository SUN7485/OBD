/**
 * MQTT Publisher - WebSocket MQTT client for telemetry publishing
 */

import * as mqtt from 'mqtt';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { TelemetryData } from './OBDManager';

const MQTT_URL = process.env.EXPO_PUBLIC_MQTT_URL || 'ws://localhost:8083/mqtt';

class MQTTPublisher {
  private client: mqtt.MqttClient | null = null;
  private connected: boolean = false;
  private carId: string = '';
  private offlineQueue: TelemetryData[] = [];
  private reconnectAttempts: number = 0;
  private maxReconnectAttempts: number = 5;

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

    this.client = mqtt.connect(MQTT_URL, {
      clientId: `fleet_mobile_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
      keepalive: 60,
      reconnectPeriod: 0,
      protocolVersion: 4,
    });

    return new Promise((resolve) => {
      const timeout = setTimeout(() => resolve(this.connected), 5000);

      this.client?.on('connect', () => {
        console.log('MQTT connected');
        this.connected = true;
        this.reconnectAttempts = 0;
        this.drainOfflineQueue();
        clearTimeout(timeout);
        resolve(true);
      });

      this.client?.on('error', (error: Error) => {
        console.error('MQTT error:', error);
        this.connected = false;
        clearTimeout(timeout);
        resolve(false);
      });
    });
  }

  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.log('Max reconnect attempts reached');
      return;
    }

    this.reconnectAttempts++;
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);

    console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);

    setTimeout(() => {
      this.connect();
    }, delay);
  }

  async publishTelemetry(data: TelemetryData): Promise<void> {
    const topic = `telemetry/${this.carId}`;
    const payload = JSON.stringify({
      rpm: data.rpm,
      speed: data.speed,
      coolant_temp: data.coolantTemp,
      engine_load: data.engineLoad,
      fuel_level: data.fuelLevel,
      throttle_position: data.throttle,
      latitude: data.latitude,
      longitude: data.longitude,
      dtc_codes: data.dtcCodes,
      timestamp: data.timestamp,
    });

    if (this.connected && this.client) {
      this.client.publish(topic, payload, { qos: 1 });
    } else {
      this.offlineQueue.push(data);
      await this.saveOfflineQueue();
      console.log('Queued telemetry offline, queue size:', this.offlineQueue.length);
    }
  }

  private async drainOfflineQueue(): Promise<void> {
    if (!this.connected || !this.client || this.offlineQueue.length === 0) return;

    console.log(`Draining ${this.offlineQueue.length} offline telemetry records`);

    for (const data of this.offlineQueue) {
      const topic = `telemetry/${this.carId}`;
      const payload = JSON.stringify({
        rpm: data.rpm,
        speed: data.speed,
        coolant_temp: data.coolantTemp,
        engine_load: data.engineLoad,
        fuel_level: data.fuelLevel,
        throttle_position: data.throttle,
        latitude: data.latitude,
        longitude: data.longitude,
        dtc_codes: data.dtcCodes,
        timestamp: data.timestamp,
      });

      this.client.publish(topic, payload, { qos: 1 });
    }

    this.offlineQueue = [];
    await this.saveOfflineQueue();
  }

  async disconnect(): Promise<void> {
    if (this.client && this.connected) {
      this.client.end();
    }
    this.client = null;
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