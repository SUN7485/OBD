/**
 * Location Service - GPS tracking using expo-location
 */

import * as Location from 'expo-location';
import * as TaskManager from 'expo-task-manager';
import * as BackgroundFetch from 'expo-background-fetch';
import { Platform } from 'react-native';

const LOCATION_TASK = 'background-location-task';
const FOREGROUND_INTERVAL = 5000;

interface LocationData {
  latitude: number;
  longitude: number;
  altitude?: number;
  accuracy?: number;
  speed?: number;
  heading?: number;
  timestamp: number;
}

type LocationCallback = (location: LocationData) => void;

class FleetLocationService {
  private watchId: Location.LocationSubscription | null = null;
  private backgroundCallback: LocationCallback | null = null;
  private isTracking: boolean = false;

  async requestPermissions(): Promise<boolean> {
    const { status } = await Location.requestForegroundPermissionsAsync();
    if (status !== 'granted') {
      return false;
    }

    if (Platform.OS === 'android') {
      const backgroundStatus = await Location.requestBackgroundPermissionsAsync();
      return backgroundStatus.status === 'granted';
    }

    return true;
  }

  async getCurrentLocation(): Promise<LocationData | null> {
    const hasPermission = await this.requestPermissions();
    if (!hasPermission) return null;

    try {
      const location = await Location.getCurrentPositionAsync({
        accuracy: Location.Accuracy.High,
        maximumAge: 10000,
      });

      return {
        latitude: location.coords.latitude,
        longitude: location.coords.longitude,
        altitude: location.coords.altitude ?? undefined,
        accuracy: location.coords.accuracy ?? undefined,
        speed: location.coords.speed ?? undefined,
        heading: location.coords.heading ?? undefined,
        timestamp: location.timestamp,
      };
    } catch (error) {
      console.error('Get location error:', error);
      return null;
    }
  }

  async startTracking(callback: LocationCallback): Promise<void> {
    const hasPermission = await this.requestPermissions();
    if (!hasPermission) {
      callback({ latitude: 0, longitude: 0, timestamp: 0 });
      return;
    }

    this.backgroundCallback = callback;
    this.isTracking = true;

    this.watchId = await Location.watchPositionAsync(
      {
        accuracy: Location.Accuracy.High,
        timeInterval: FOREGROUND_INTERVAL,
        distanceInterval: 10,
      },
      (location) => {
        const locData: LocationData = {
          latitude: location.coords.latitude,
          longitude: location.coords.longitude,
          altitude: location.coords.altitude ?? undefined,
          accuracy: location.coords.accuracy ?? undefined,
          speed: location.coords.speed ?? undefined,
          heading: location.coords.heading ?? undefined,
          timestamp: location.timestamp,
        };
        this.backgroundCallback?.(locData);
      }
    );
  }

  stopTracking(): void {
    this.isTracking = false;
    this.watchId?.remove();
    this.watchId = null;
    this.backgroundCallback = null;
  }

  isActive(): boolean {
    return this.isTracking;
  }
}

export default new FleetLocationService();