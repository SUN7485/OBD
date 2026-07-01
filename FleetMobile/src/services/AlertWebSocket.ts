/**
 * WebSocket Alert Service - Real-time alerts from backend
 */

import { Alert } from 'react-native';
import api from './api';

interface AlertPayload {
  severity: 'info' | 'warning' | 'critical';
  message: string;
  car_id?: string;
  created_at?: string;
}

type AlertHandler = (alert: AlertPayload) => void;

class WebSocketAlertService {
  private ws: WebSocket | null = null;
  private token: string = '';
  private handlers: AlertHandler[] = [];
  private reconnectAttempts: number = 0;
  private maxReconnectAttempts: number = 5;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private connected: boolean = false;

  setToken(token: string): void {
    this.token = token;
  }

  addHandler(handler: AlertHandler): void {
    this.handlers.push(handler);
  }

  removeHandler(handler: AlertHandler): void {
    this.handlers = this.handlers.filter(h => h !== handler);
  }

  private notifyHandlers(alert: AlertPayload): void {
    this.handlers.forEach(h => h(alert));
  }

  private showAlert(data: AlertPayload): void {
    Alert.alert(
      data.severity.toUpperCase(),
      data.message,
      [{ text: 'OK', style: 'default' }]
    );
  }

  private scheduleReconnect(apiUrl: string): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) return;

    this.reconnectAttempts++;
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);

    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
    }

    this.reconnectTimer = setTimeout(() => {
      this.connect(apiUrl);
    }, delay);
  }

  constructor() {
    api.addTokenRefreshListener((newToken: string) => {
      this.setToken(newToken);
      const currentHost = this.getCurrentHost();
      if (currentHost) {
        this.disconnect();
        this.connect(currentHost);
      }
    });
  }

  private lastHost: string | null = null;

  private getCurrentHost(): string | null {
    return this.lastHost;
  }

  connect(apiUrl: string = 'ws://localhost:8000'): boolean {
    if (!this.token) {
      console.warn('No auth token set, cannot connect to WebSocket');
      return false;
    }

    const fullApiUrl = apiUrl.startsWith('http') ? apiUrl.replace(/^http/, 'ws') : apiUrl;
    this.lastHost = fullApiUrl;
    const wsUrl = `${fullApiUrl}/api/v1/ws?token=${this.token}`;

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log('WebSocket connected');
        this.connected = true;
        this.reconnectAttempts = 0;
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'alert') {
            this.notifyHandlers(data.data);
            this.showAlert(data.data);
          }
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e);
        }
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      this.ws.onclose = () => {
        console.log('WebSocket closed');
        this.connected = false;
        this.scheduleReconnect(apiUrl);
      };

      return true;
    } catch (e) {
      console.error('WebSocket connect error:', e);
      return false;
    }
  }

  disconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    this.connected = false;
  }

  isReady(): boolean {
    return this.connected;
  }
}

export default new WebSocketAlertService();