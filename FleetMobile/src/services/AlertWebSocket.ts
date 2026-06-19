/**
 * WebSocket Alert Service - Real-time alerts from backend
 */

import { Alert } from 'react-native';

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
      [{ text: 'OK', style: 'default' }],
      {
        title: data.severity.toUpperCase(),
        message: data.message,
      }
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

  connect(apiUrl: string = 'http://localhost:8000'): boolean {
    if (!this.token) {
      console.warn('No auth token set, cannot connect to WebSocket');
      return false;
    }

    const wsUrl = apiUrl.replace(/^http/, 'ws') + `/api/v1/ws?token=${this.token}`;

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

type AlertHandler = (alert: AlertPayload) => void;

class WebSocketAlertService {
  private ws: WebSocket | null = null;
  private token: string = '';
  private handlers: AlertHandler[] = [];
  private reconnectAttempts: number = 0;
  private maxReconnectAttempts: number = 5;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;

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

  connect(apiUrl: string = 'http://localhost:8000'): boolean {
    if (!this.token) {
      console.warn('No auth token set, cannot connect to WebSocket');
      return false;
    }

    const wsUrl = apiUrl.replace(/^http/, 'ws') + `/api/v1/ws?token=${this.token}`;

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log('WebSocket connected');
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
        this.scheduleReconnect();
      };

      return true;
    } catch (e) {
      console.error('WebSocket connect error:', e);
      return false;
    }
  }

  private showAlert(data: AlertPayload): void {
    const colors = {
      info: '#1890ff',
      warning: '#faad14',
      critical: '#ff4d4f',
    };

    Alert.alert(
      data.severity.toUpperCase(),
      data.message,
      [{ text: 'OK', style: 'default' }],
      {
        title: data.severity.toUpperCase(),
        message: data.message,
      }
    );
  }

  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) return;

    this.reconnectAttempts++;
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);

    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
    }

    this.reconnectTimer = setTimeout(() => {
      this.connect();
    }, delay);
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
  }
}