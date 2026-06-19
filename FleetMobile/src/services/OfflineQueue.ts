/**
 * Offline Queue - Store telemetry locally when offline
 */

import AsyncStorage from '@react-native-async-storage/async-storage';

const QUEUE_KEY = 'telemetry_offline_queue';
const MAX_QUEUE_SIZE = 500;
const DRAIN_BATCH_SIZE = 50;

interface QueuedTelemetry {
  car_id: string;
  speed: number;
  rpm: number;
  coolant_temp: number;
  engine_load: number;
  throttle: number;
  fuel_level: number;
  latitude?: number;
  longitude?: number;
  timestamp: string;
}

class OfflineQueueStorage {
  private queue: QueuedTelemetry[] = [];
  private initialized: boolean = false;

  async load(): Promise<void> {
    if (this.initialized) return;

    try {
      const stored = await AsyncStorage.getItem(QUEUE_KEY);
      if (stored) {
        this.queue = JSON.parse(stored);
      }
    } catch (error) {
      console.error('Failed to load offline queue:', error);
      this.queue = [];
    }
    this.initialized = true;
  }

  private async persist(): Promise<void> {
    try {
      await AsyncStorage.setItem(QUEUE_KEY, JSON.stringify(this.queue));
    } catch (error) {
      console.error('Failed to persist offline queue:', error);
    }
  }

  async enqueue(data: QueuedTelemetry): Promise<void> {
    await this.load();

    this.queue.push(data);

    if (this.queue.length > MAX_QUEUE_SIZE) {
      this.queue = this.queue.slice(-MAX_QUEUE_SIZE);
    }

    await this.persist();
  }

  async dequeue(): Promise<void> {
    await this.load();

    if (this.queue.length > 0) {
      this.queue.shift();
      await this.persist();
    }
  }

  async getAll(): Promise<QueuedTelemetry[]> {
    await this.load();
    return [...this.queue];
  }

  async clear(): Promise<void> {
    this.queue = [];
    await this.persist();
  }

  async getBatch(count: number = DRAIN_BATCH_SIZE): Promise<QueuedTelemetry[]> {
    await this.load();
    return this.queue.slice(0, count);
  }

  removeBatch(count: number): void {
    this.queue = this.queue.slice(count);
  }

  async size(): Promise<number> {
    await this.load();
    return this.queue.length;
  }
}

export default new OfflineQueueStorage();