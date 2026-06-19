/**
 * OBD Manager - Handles BLE communication with ELM327 OBD devices
 */

import { BleManager, Device, Subscription } from 'react-native-ble-plx';
import { OBD_PIDS, OBD_DTC, parsePIDResponse, parseDTCResponse, getDTCDescription } from './OBDService';

const OBD_SERVICE_UUID = '0000fff0-0000-1000-8000-00805f9b34fb';
const OBD_CHAR_UUID = '0000fff1-0000-1000-8000-00805f9bfb';
const ELM_PROMPT = '>';

export interface TelemetryData {
  speed: number;
  rpm: number;
  coolantTemp: number;
  engineLoad: number;
  throttle: number;
  fuelLevel: number;
  intakeAirTemp: number;
  mafAirFlow: number;
  dtcCodes: string[];
  timestamp: string;
}

class OBDManager {
  private manager: BleManager;
  private device: Device | null = null;
  private writeCharId: string | null = null;
  private readCharId: string | null = null;
  private connected: boolean = false;
  private pollTimer: ReturnType<typeof setInterval> | null = null;
  private responseBuffer: string = '';

  constructor() {
    this.manager = new BleManager();
  }

  startScan(callback: (device: Device) => void, onError?: (error: string) => void): Subscription {
    return this.manager.startDeviceScan(
      null,
      { allowDuplicates: false },
      (error, device) => {
        if (error) {
          onError?.(error.message || 'Scan error');
          return;
        }
        if (device && (device.name?.toUpperCase().includes('OBD') || 
            device.name?.toUpperCase().includes('ELM') ||
            device.name?.toUpperCase().includes('VEELINK') ||
            device.name?.toUpperCase().includes('OBDLINK'))) {
          callback(device);
        }
      }
    );
  }

  stopScan(): void {
    this.manager.stopDeviceScan();
  }

  async connect(device: Device): Promise<boolean> {
    try {
      const connectedDevice = await this.manager.connectToDevice(device.id, {
        timeout: 30000,
        requestMTU: 517,
      });

      await connectedDevice.discoverAllServicesAndCharacteristics();
      const services = await connectedDevice.services();

      let found = false;
      for (const svc of services) {
        const characteristics = await connectedDevice.characteristicsForService(svc.uuid);
        for (const char of characteristics) {
          if (char.isWritableWithResponse || char.isWritableWithoutResponse) {
            this.writeCharId = char.uuid;
          }
          if (char.isReadable || char.hasIndications || char.hasNotifications) {
            this.readCharId = char.uuid;
          }
          if (char.uuid.toLowerCase().includes('fff1') || char.uuid.toLowerCase().includes('fff2')) {
            found = true;
          }
        }
      }

      if (!found && !this.writeCharId) {
        const allChars = await connectedDevice.characteristics();
        for (const char of allChars) {
          if (char.isWritableWithResponse || char.isWritableWithoutResponse) {
            this.writeCharId = char.uuid;
          }
          if (char.isReadable || char.hasIndications || char.hasNotifications) {
            this.readCharId = char.uuid;
          }
        }
      }

      this.device = connectedDevice;
      this.connected = true;
      this.responseBuffer = '';

      if (this.readCharId) {
        this.manager.monitorCharacteristicForService(
          OBD_SERVICE_UUID,
          this.readCharId,
          (error, characteristic) => {
            if (error) return;
            if (characteristic?.value) {
              const decoded = this.base64Decode(characteristic.value);
              this.responseBuffer += decoded;
            }
          }
        );
      }

      await this.initDevice();
      return true;
    } catch (e: unknown) {
      console.error('Connect error:', e);
      this.connected = false;
      return false;
    }
  }

  private async initDevice(): Promise<void> {
    await this.sendCommand('ATZ');
    await new Promise(resolve => setTimeout(resolve, 100));
    await this.sendCommand('ATE0');
    await this.sendCommand('ATL0');
    await this.sendCommand('ATSP0');
    await this.sendCommand('ATS0');
  }

  private base64Encode(str: string): string {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
    let result = '';
    let i = 0;

    while (i < str.length) {
      const a = str.charCodeAt(i++);
      const b = i < str.length ? str.charCodeAt(i++) : 0;
      const c = i < str.length ? str.charCodeAt(i++) : 0;

      result += chars.charAt(a >> 2);
      result += chars.charAt(((a & 3) << 4) | (b >> 4));
      result += i > str.length + 1 ? '=' : chars.charAt(((b & 15) << 2) | (c >> 6));
      result += i > str.length ? '=' : chars.charAt(c & 63);
    }

    return result;
  }

  private base64Decode(str: string): string {
    try {
      let base64 = str.replace(/-/g, '+').replace(/_/g, '/').padEnd(str.length + (4 - (str.length % 4)) % 4, '=');
      const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=';
      let result = '';

      for (let i = 0; i < base64.length; i += 4) {
        const a = chars.indexOf(base64.charAt(i));
        const b = chars.indexOf(base64.charAt(i + 1));
        const c = chars.indexOf(base64.charAt(i + 2));
        const d = chars.indexOf(base64.charAt(i + 3));

        const bitmap = (a << 18) | (b << 12) | (c << 6) | d;
        result += String.fromCharCode((bitmap >> 16) & 0xff, (bitmap >> 8) & 0xff, bitmap & 0xff);
      }

      return result;
    } catch {
      return '';
    }
  }

  async sendCommand(cmd: string): Promise<string> {
    if (!this.device || !this.writeCharId) return '';

    try {
      this.responseBuffer = '';
      const fullCmd = cmd + '\r';
      const base64Cmd = this.base64Encode(fullCmd);

      await this.device.writeCharacteristicWithResponseForService(
        OBD_SERVICE_UUID,
        this.writeCharId,
        base64Cmd
      );

      const response = await this.waitForResponse(2000);
      return response;
    } catch (e: unknown) {
      console.error('Command error:', cmd, e);
      return '';
    }
  }

  private waitForResponse(timeout: number): Promise<string> {
    return new Promise((resolve) => {
      let resolved = false;
      const timeoutId = setTimeout(() => {
        if (!resolved) {
          resolved = true;
          resolve(this.responseBuffer);
        }
      }, timeout);

      const checkInterval = setInterval(() => {
        if (this.responseBuffer.includes('>')) {
          if (!resolved) {
            resolved = true;
            clearTimeout(timeoutId);
            clearInterval(checkInterval);
            const cleanResponse = this.responseBuffer.replace(/>/g, '').trim();
            resolve(cleanResponse);
          }
        }
      }, 100);
    });
  }

  async readTelemetry(): Promise<TelemetryData> {
    const ts = new Date().toISOString();

    const [speed, rpm, coolantTemp, engineLoad, throttle, fuelLevel, intakeAirTemp] = await Promise.all([
      this.readPID(OBD_PIDS.VEHICLE_SPEED),
      this.readPID(OBD_PIDS.ENGINE_RPM),
      this.readPID(OBD_PIDS.COOLANT_TEMP),
      this.readPID(OBD_PIDS.ENGINE_LOAD),
      this.readPID(OBD_PIDS.THROTTLE_POSITION),
      this.readPID(OBD_PIDS.FUEL_GAUGE_LEVEL),
      this.readPID(OBD_PIDS.INTAKE_AIR_TEMP),
    ]);

    return {
      speed: speed ?? 0,
      rpm: rpm ?? 0,
      coolantTemp: coolantTemp ?? 0,
      engineLoad: engineLoad ?? 0,
      throttle: throttle ?? 0,
      fuelLevel: fuelLevel ?? 0,
      intakeAirTemp: intakeAirTemp ?? 0,
      mafAirFlow: 0,
      dtcCodes: [],
      timestamp: ts,
    };
  }

  private async readPID(pid: string): Promise<number | null> {
    try {
      const response = await this.sendCommand(pid);
      return parsePIDResponse(pid, response);
    } catch {
      return null;
    }
  }

  async readDTCs(): Promise<string[]> {
    const response = await this.sendCommand(OBD_DTC.READ_DTC);
    return parseDTCResponse(response);
  }

  async clearDTCs(): Promise<boolean> {
    const r = await this.sendCommand(OBD_DTC.CLEAR_DTC);
    return r.includes('44');
  }

  startPolling(callback: (data: TelemetryData) => void, intervalMs: number = 1000): void {
    this.stopPolling();
    this.pollTimer = setInterval(async () => {
      try {
        const data = await this.readTelemetry();
        callback(data);
      } catch (e) {
        console.error('Polling error:', e);
      }
    }, intervalMs);
  }

  stopPolling(): void {
    if (this.pollTimer) {
      clearInterval(this.pollTimer);
      this.pollTimer = null;
    }
  }

  async disconnect(): Promise<void> {
    this.stopPolling();
    if (this.device) {
      try {
        await this.manager.cancelDeviceConnection(this.device.id);
      } catch (e) {
        console.error('Disconnect error:', e);
      }
    }
    this.device = null;
    this.writeCharId = null;
    this.readCharId = null;
    this.connected = false;
  }

  isConnected(): boolean {
    return this.connected;
  }

  getManager(): BleManager {
    return this.manager;
  }
}

export default new OBDManager();