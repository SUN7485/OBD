/**
 * Fleet Mobile Store - State management with secure token storage
 */

import { create } from 'zustand';
import * as SecureStore from 'expo-secure-store';

interface User {
  id: string;
  email: string;
  organization_id: string;
  organization_name: string;
  role: string;
  full_name?: string;
}

interface AuthState {
  token: string | null;
  refreshToken: string | null;
  user: User | null;
  isAuthenticated: boolean;
  setAuth: (token: string, refreshToken: string, user: User) => Promise<void>;
  logout: () => Promise<void>;
  checkAuth: () => Promise<boolean>;
}

const AUTH_KEY = 'auth_data';

export const useAuthStore = create<AuthState>()((set) => ({
  token: null,
  refreshToken: null,
  user: null,
  isAuthenticated: false,

  setAuth: async (token, refreshToken, user) => {
    try {
      await SecureStore.setItemAsync(AUTH_KEY, JSON.stringify({ token, refreshToken, user }));
      set({ token, refreshToken, user, isAuthenticated: true });
    } catch (error) {
      console.error('Failed to store auth:', error);
      set({ token, refreshToken, user, isAuthenticated: true });
    }
  },

  logout: async () => {
    try {
      await SecureStore.deleteItemAsync(AUTH_KEY);
    } catch (error) {
      console.error('Failed to clear auth:', error);
    }
    set({ token: null, refreshToken: null, user: null, isAuthenticated: false });
  },

  checkAuth: async () => {
    try {
      const data = await SecureStore.getItemAsync(AUTH_KEY);
      if (data) {
        const { token, refreshToken, user } = JSON.parse(data);
        set({ token, refreshToken, user, isAuthenticated: true });
        return true;
      }
    } catch (error) {
      console.error('Failed to check auth:', error);
    }
    return false;
  },
}));

interface TelemetryData {
  speed: number;
  rpm: number;
  coolant_temp: number;
  engine_load: number;
  fuel_level: number;
  throttle: number;
  latitude?: number;
  longitude?: number;
  timestamp: string;
}

interface OBDState {
  isConnected: boolean;
  connectedDevice: string | null;
  telemetry: TelemetryData | null;
  dtcCodes: string[];
  setConnected: (device: string) => void;
  setDisconnected: () => void;
  updateTelemetry: (data: TelemetryData) => void;
  setDTCCodes: (codes: string[]) => void;
}

export const useOBDStore = create<OBDState>()((set) => ({
  isConnected: false,
  connectedDevice: null,
  telemetry: null,
  dtcCodes: [],
  setConnected: (device) => set({ isConnected: true, connectedDevice: device }),
  setDisconnected: () => set({ isConnected: false, connectedDevice: null, telemetry: null }),
  updateTelemetry: (data) => set({ telemetry: data }),
  setDTCCodes: (codes) => set({ dtcCodes: codes }),
}));

interface Alert {
  id: string;
  severity: 'info' | 'warning' | 'critical';
  message: string;
  is_read: boolean;
  created_at: string;
}

interface AlertState {
  alerts: Alert[];
  unreadCount: number;
  setAlerts: (alerts: Alert[]) => void;
  addAlert: (alert: Alert) => void;
}

export const useAlertStore = create<AlertState>()((set) => ({
  alerts: [],
  unreadCount: 0,
  setAlerts: (alerts) => set({ alerts, unreadCount: alerts.filter(a => !a.is_read).length }),
  addAlert: (alert) => set((state) => ({
    alerts: [alert, ...state.alerts],
    unreadCount: state.unreadCount + 1
  })),
}));