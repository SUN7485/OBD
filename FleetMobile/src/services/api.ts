/**
 * API Service - Communication layer for Fleet OBD Backend
 */

import axios, { AxiosInstance } from 'axios';
import * as SecureStore from 'expo-secure-store';

const API_BASE_URL = process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8000';
const API_KEY_HEADER = 'X-API-Key';

interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
  organization_id: string;
}

interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

interface TelemetryPayload {
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

interface Car {
  id: string;
  name: string;
  make: string;
  model: string;
  year: number;
  vin: string;
  license_plate: string;
  status: string;
}

interface Alert {
  id: string;
  car_id: string;
  severity: 'info' | 'warning' | 'critical';
  message: string;
  is_read: boolean;
  created_at: string;
}

interface AIRequest {
  message: string;
  car_id?: string;
  context?: Record<string, unknown>;
}

interface AIResponse {
  message: string;
  actions?: Record<string, unknown>;
}

const AUTH_STORAGE_KEY = 'auth_data';
const MQTT_STORAGE_KEY = 'mqtt_config';

class FleetAPI {
  private client: AxiosInstance;
  private deviceApiKey: string | null = null;

  constructor() {
    this.client = axios.create({
      baseURL: `${API_BASE_URL}/api/v1`,
      timeout: 10000,
      headers: { 'Content-Type': 'application/json' },
    });

    this.client.interceptors.request.use(
      async (config) => {
        const authData = await SecureStore.getItemAsync(AUTH_STORAGE_KEY);
        if (authData) {
          const auth = JSON.parse(authData) as { token: string };
          config.headers.Authorization = `Bearer ${auth.token}`;
        }
        if (this.deviceApiKey) {
          config.headers[API_KEY_HEADER] = this.deviceApiKey;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    this.client.interceptors.response.use(
      (response) => response,
      async (error) => {
        if (error.response?.status === 401) {
          const refreshed = await this.refreshToken();
          if (!refreshed) {
            await this.logout();
          }
        }
        return Promise.reject(error);
      }
    );
  }

  static getHost(): string {
    return API_BASE_URL.replace(/^https?/, 'ws');
  }

  setDeviceApiKey(key: string) {
    this.deviceApiKey = key;
  }

  async login(email: string, password: string): Promise<LoginResponse> {
    const { data } = await this.client.post<LoginResponse>('/auth/login', { email, password });
    await SecureStore.setItemAsync(AUTH_STORAGE_KEY, JSON.stringify({
      token: data.access_token,
      refreshToken: data.refresh_token,
      user: data.user,
    }));
    return data;
  }

  async register(email: string, password: string, fullName: string, orgName: string): Promise<LoginResponse> {
    const { data } = await this.client.post<LoginResponse>('/auth/register', {
      email,
      password,
      full_name: fullName,
      organization_name: orgName,
    });
    return data;
  }

  async refreshToken(): Promise<boolean> {
    try {
      const authData = await SecureStore.getItemAsync(AUTH_STORAGE_KEY);
      if (!authData) return false;
      const auth = JSON.parse(authData) as { refreshToken: string };

      const { data } = await this.client.post<LoginResponse>('/auth/refresh', {
        refresh_token: auth.refreshToken,
      });

      await SecureStore.setItemAsync(AUTH_STORAGE_KEY, JSON.stringify({
        token: data.access_token,
        refreshToken: data.refresh_token,
        user: data.user,
      }));
      return true;
    } catch {
      return false;
    }
  }

  async logout(): Promise<void> {
    await SecureStore.deleteItemAsync(AUTH_STORAGE_KEY);
    await SecureStore.deleteItemAsync(MQTT_STORAGE_KEY);
    this.deviceApiKey = null;
  }

  async getUser(): Promise<User | null> {
    try {
      const authData = await SecureStore.getItemAsync(AUTH_STORAGE_KEY);
      if (!authData) return null;
      const auth = JSON.parse(authData);
      return auth.user;
    } catch {
      return null;
    }
  }

  async getToken(): Promise<string | null> {
    try {
      const authData = await SecureStore.getItemAsync(AUTH_STORAGE_KEY);
      if (!authData) return null;
      const auth = JSON.parse(authData);
      return auth.token;
    } catch {
      return null;
    }
  }

  async ingestTelemetry(payload: TelemetryPayload): Promise<void> {
    await this.client.post('/telemetry/ingest', payload);
  }

  async getTelemetryHistory(carId: string, startTime?: string, endTime?: string): Promise<TelemetryPayload[]> {
    const params: Record<string, string> = { car_id: carId };
    if (startTime) params.start_time = startTime;
    if (endTime) params.end_time = endTime;
    const { data } = await this.client.get<{ data: TelemetryPayload[] }>('/telemetry/history', { params });
    return data.data;
  }

  async getCars(): Promise<Car[]> {
    const { data } = await this.client.get<{ data: Car[] }>('/fleet/cars');
    return data.data;
  }

  async createCar(car: Partial<Car>): Promise<Car> {
    const { data } = await this.client.post<{ data: Car }>('/fleet/cars', car);
    return data.data;
  }

  async updateCar(id: string, car: Partial<Car>): Promise<Car> {
    const { data } = await this.client.put<{ data: Car }>(`/fleet/cars/${id}`, car);
    return data.data;
  }

  async deleteCar(id: string): Promise<void> {
    await this.client.delete(`/fleet/cars/${id}`);
  }

  async getAlerts(carId?: string, severity?: string): Promise<Alert[]> {
    const params: Record<string, string> = {};
    if (carId) params.car_id = carId;
    if (severity) params.severity = severity;
    const { data } = await this.client.get<{ data: Alert[] }>('/alerts', { params });
    return data.data;
  }

  async markAlertRead(id: string): Promise<void> {
    await this.client.patch(`/alerts/${id}/read`);
  }

  async resolveAlert(id: string): Promise<void> {
    await this.client.patch(`/alerts/${id}/resolve`);
  }

  async chatWithAI(request: AIRequest): Promise<AIResponse> {
    const { data } = await this.client.post<AIResponse>('/ai/chat', request);
    return data;
  }

  async explainDTC(code: string, carId?: string): Promise<AIResponse> {
    const { data } = await this.client.post<AIResponse>('/ai/dtc-explain', { code, car_id: carId });
    return data;
  }
}

export default new FleetAPI();
export type { TelemetryPayload, Car, Alert, AIRequest, AIResponse, User };