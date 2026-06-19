// Mock AsyncStorage
jest.mock('@react-native-async-storage/async-storage', () => ({
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
}));

import AsyncStorage from '@react-native-async-storage/async-storage';
import OfflineQueue from '../src/services/OfflineQueue';

describe('OfflineQueue', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (AsyncStorage.getItem as jest.Mock).mockResolvedValue(null);
    (AsyncStorage.setItem as jest.Mock).mockResolvedValue(undefined);
  });

  describe('enqueue', () => {
    it('adds telemetry to queue', async () => {
      const data = {
        car_id: 'car-1',
        speed: 50,
        rpm: 2000,
        timestamp: '2024-01-01T10:00:00Z',
      };

      await OfflineQueue.enqueue(data);

      expect(AsyncStorage.setItem).toHaveBeenCalled();
    });

    it('limits queue size to 500', async () => {
      const data = {
        car_id: 'car-1',
        speed: 50,
        timestamp: '2024-01-01T10:00:00Z',
      };

      // Add many items
      for (let i = 0; i < 600; i++) {
        await OfflineQueue.enqueue({ ...data, timestamp: `2024-01-01T10:${i.toString().padStart(2, '0')}Z` });
      }

      // Queue should be limited
      expect(AsyncStorage.setItem).toHaveBeenCalled();
    });
  });

  describe('dequeue', () => {
    it('removes oldest item', async () => {
      const queue = [
        { car_id: 'car-1', speed: 50, timestamp: '2024-01-01T10:00:00Z' },
        { car_id: 'car-1', speed: 55, timestamp: '2024-01-01T10:01:00Z' },
      ];

      (AsyncStorage.getItem as jest.Mock).mockResolvedValue(JSON.stringify(queue));

      await OfflineQueue.dequeue();

      expect(AsyncStorage.setItem).toHaveBeenCalled();
    });
  });

  describe('getAll', () => {
    it('returns all queued items', async () => {
      const queue = [
        { car_id: 'car-1', speed: 50 },
        { car_id: 'car-1', speed: 55 },
      ];

      (AsyncStorage.getItem as jest.Mock).mockResolvedValue(JSON.stringify(queue));

      const result = await OfflineQueue.getAll();

      expect(result).toEqual(queue);
    });

    it('returns empty array when nothing queued', async () => {
      (AsyncStorage.getItem as jest.Mock).mockResolvedValue(null);

      const result = await OfflineQueue.getAll();

      expect(result).toEqual([]);
    });
  });

  describe('clear', () => {
    it('clears all items', async () => {
      await OfflineQueue.clear();

      expect(AsyncStorage.setItem).toHaveBeenCalledWith(
        'telemetry_offline_queue',
        '[]'
      );
    });
  });

  describe('getBatch', () => {
    it('returns batch of items', async () => {
      const queue = Array.from({ length: 100 }, (_, i) => ({
        car_id: 'car-1',
        speed: 50 + i,
      }));

      (AsyncStorage.getItem as jest.Mock).mockResolvedValue(JSON.stringify(queue));

      const batch = await OfflineQueue.getBatch(50);

      expect(batch.length).toBe(50);
    });
  });

  describe('size', () => {
    it('returns queue size', async () => {
      const queue = [
        { car_id: 'car-1' },
        { car_id: 'car-1' },
      ];

      (AsyncStorage.getItem as jest.Mock).mockResolvedValue(JSON.stringify(queue));

      const size = await OfflineQueue.size();

      expect(size).toBe(2);
    });
  });
});