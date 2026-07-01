import React, { useState, useEffect, useCallback, useRef, memo } from 'react';
import { View, Text, StyleSheet, FlatList, TouchableOpacity, Alert, Platform, PermissionsAndroid, AppState } from 'react-native';
import { Device, Subscription } from 'react-native-ble-plx';
import { useOBDStore } from '../store';
import OBDManager from '../services/OBDManager';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import * as SecureStore from 'expo-secure-store';

const OBD_SERVICE_UUID = '0000fff0-0000-1000-8000-00805f9b34fb';
const CAR_ID_KEY = 'selected_car_id';

export default function BLEConnectScreen() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [scanning, setScanning] = useState(false);
  const manager = OBDManager.getManager();
  const scanSubscriptionRef = useRef<Subscription | null>(null);
  const scanSuccessFlagRef = useRef(false);
  const scanTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const appStateListenerRef = useRef<{ remove: () => void } | null>(null);
  const [scanFingerprint, setScanFingerprint] = useState(0);
  const appState = AppState.currentState;
  const { setConnected, setDisconnected, isConnected } = useOBDStore();

  const requestPermissions = useCallback(async () => {
    if (Platform.OS === 'android') {
      try {
        const granted = await PermissionsAndroid.requestMultiple([
          PermissionsAndroid.PERMISSIONS.ACCESS_FINE_LOCATION,
        ]);
        const allGranted = Object.values(granted).every(
          status => status === PermissionsAndroid.RESULTS.GRANTED
        );
        if (!allGranted) {
          Alert.alert('Permissions Required', 'Please grant location permission for Bluetooth scanning');
        }
        return allGranted;
      } catch (err) {
        console.warn('Permission error:', err);
        return false;
      }
    }
    return true;
  }, []);

  useEffect(() => {
    requestPermissions();

    appStateListenerRef.current = AppState.addEventListener('change', () => {});

    return () => {
      if (appStateListenerRef.current) {
        appStateListenerRef.current.remove();
      }
      if (scanSubscriptionRef.current) {
        scanSubscriptionRef.current.remove();
        scanSubscriptionRef.current = null;
      }
      manager.stopDeviceScan();
      if (scanTimerRef.current) {
        clearTimeout(scanTimerRef.current);
        scanTimerRef.current = null;
      }
    };
  }, [manager, requestPermissions]);

  const startScan = useCallback(async () => {
    setDevices([]);
    setScanning(true);
    scanSuccessFlagRef.current = false;

    manager.stopDeviceScan();
    if (scanSubscriptionRef.current) {
      try { await scanSubscriptionRef.current.remove(); } catch { /* noop */ }
      scanSubscriptionRef.current = null;
    }

    if (scanTimerRef.current) {
      clearTimeout(scanTimerRef.current);
      scanTimerRef.current = null;
    }

    try {
      await manager.startDeviceScan(
        null,
        { allowDuplicates: false },
        (error, device) => {
          if (error) {
            console.error('Scan error:', error);
            Alert.alert('Error', 'Failed to scan for devices');
            setScanning(false);
            scanSuccessFlagRef.current = false;
            return;
          }

          if (device && device.name) {
            const name = device.name.toUpperCase();
            if (name.includes('OBD') || name.includes('ELM') || name.includes('VEELINK') || name.includes('OBDLINK')) {
              scanSuccessFlagRef.current = true;
              setDevices(prev => {
                if (prev.find(d => d.id === device.id)) return prev;
                return [...prev, device];
              });
            }
          }
        }
      );
    } catch (err) {
      setScanning(false);
      return;
    }

    scanTimerRef.current = setTimeout(() => {
      if (scanSubscriptionRef.current) {
        scanSubscriptionRef.current.remove();
        scanSubscriptionRef.current = null;
      }
      manager.stopDeviceScan();
      setScanning(false);
      scanSuccessFlagRef.current = false;
      scanTimerRef.current = null;
    }, 10000);

    setScanFingerprint(f => f + 1);
  }, [manager]);

  const connectToDevice = useCallback(async (device: Device) => {
    try {
      setScanning(false);
      if (scanSubscriptionRef.current) {
        scanSubscriptionRef.current.remove();
        scanSubscriptionRef.current = null;
      }
      manager.stopDeviceScan();

      Alert.alert('Connecting', `Connecting to ${device.name}...`);

      const connectedDevice = await manager.connectToDevice(device.id, {
        timeout: 30000,
        requestMTU: 517,
      });

      await connectedDevice.discoverAllServicesAndCharacteristics();

      const services = await connectedDevice.services();
      let found = false;

      for (const svc of services) {
        const chars = await connectedDevice.characteristicsForService(svc.uuid);
        for (const char of chars) {
          if (char.isWritableWithResponse || char.uuid.toLowerCase().includes('fff1')) {
            found = true;
            break;
          }
        }
        if (found) break;
      }

      if (!found) {
        Alert.alert('Error', 'Device not compatible or unsupported protocol');
        await manager.cancelDeviceConnection(device.id);
        return;
      }

      setConnected(device.name || 'OBD Device');
      Alert.alert('Success', `Connected to ${device.name}`);

      await SecureStore.setItemAsync(CAR_ID_KEY, device.id);
    } catch (error) {
      console.error('Connection error:', error);
      Alert.alert('Error', 'Failed to connect to device');
    }
  }, [manager, setConnected]);

  const disconnect = useCallback(async () => {
    try {
      setDisconnected();
      Alert.alert('Disconnected', 'OBD device disconnected');
      await SecureStore.deleteItemAsync(CAR_ID_KEY);
    } catch (error) {
      console.error('Disconnect error:', error);
    }
  }, [setDisconnected]);

  const renderDevice = useCallback(({ item }: { item: Device }) => (
    <TouchableOpacity
      style={styles.deviceCard}
      onPress={() => connectToDevice(item)}
    >
      <Icon name="bluetooth" size={32} color="#1890ff" />
      <View style={styles.deviceInfo}>
        <Text style={styles.deviceName}>{item.name || 'Unknown Device'}</Text>
        <Text style={styles.deviceId}>{item.id}</Text>
      </View>
      <Icon name="chevron-right" size={24} color="#999" />
    </TouchableOpacity>
  ), [connectToDevice]);

  const keyExtractor = useCallback((item: Device) => item.id, []);

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Connect OBD</Text>
        <Text style={styles.subtitle}>Scan for nearby Bluetooth OBD devices</Text>
      </View>

      {isConnected ? (
        <View style={styles.connectedCard}>
          <Icon name="bluetooth-connect" size={48} color="#52c41a" />
          <Text style={styles.connectedTitle}>Connected</Text>
          <Text style={styles.connectedText}>Your OBD device is connected</Text>
          <TouchableOpacity style={styles.disconnectButton} onPress={disconnect}>
            <Text style={styles.disconnectText}>Disconnect</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <>
          <TouchableOpacity
            style={[styles.scanButton, scanning && styles.scanButtonDisabled]}
            onPress={startScan}
            disabled={scanning}
          >
            <Icon name="magnify" size={24} color="#fff" />
            <Text style={styles.scanButtonText}>
              {scanning ? 'Scanning...' : 'Scan for Devices'}
            </Text>
          </TouchableOpacity>

          <Text style={styles.listTitle}>
            Available Devices ({devices.length})
          </Text>

          {devices.length === 0 ? (
            <View style={styles.emptyState}>
              <Icon name="bluetooth-off" size={64} color="#ccc" />
              <Text style={styles.emptyText}>
                {scanning ? 'Searching...' : 'No devices found'}
              </Text>
              <Text style={styles.emptyHint}>
                Make sure your OBD device is powered on
              </Text>
            </View>
          ) : (
            <FlatList
              data={devices}
              renderItem={renderDevice}
              keyExtractor={keyExtractor}
              contentContainerStyle={styles.list}
              getItemLayout={(_data, index) => ({
                length: 72,
                offset: 72 * index,
                index,
              })}
            />
          )}
        </>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f6fa',
  },
  header: {
    padding: 16,
    backgroundColor: '#0b1220',
    minHeight: 56,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#fff',
  },
  subtitle: {
    fontSize: 14,
    color: '#999',
    marginTop: 4,
  },
  scanButton: {
    flexDirection: 'row',
    backgroundColor: '#1890ff',
    margin: 16,
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 48,
  },
  scanButtonDisabled: {
    opacity: 0.6,
  },
  scanButtonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '600',
    marginLeft: 8,
  },
  listTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    marginLeft: 16,
    marginBottom: 8,
  },
  list: {
    padding: 16,
    paddingTop: 0,
  },
  deviceCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    padding: 16,
    borderRadius: 12,
    marginBottom: 12,
    minHeight: 48,
  },
  deviceInfo: {
    flex: 1,
    marginLeft: 12,
  },
  deviceName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
  },
  deviceId: {
    fontSize: 12,
    color: '#999',
    marginTop: 2,
  },
  emptyState: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 32,
  },
  emptyText: {
    fontSize: 18,
    color: '#666',
    marginTop: 16,
  },
  emptyHint: {
    fontSize: 14,
    color: '#999',
    marginTop: 8,
    textAlign: 'center',
  },
  connectedCard: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 32,
  },
  connectedTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#52c41a',
    marginTop: 16,
  },
  connectedText: {
    fontSize: 16,
    color: '#666',
    marginTop: 8,
  },
  disconnectButton: {
    marginTop: 24,
    paddingHorizontal: 32,
    paddingVertical: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#ff4d4f',
    minHeight: 44,
  },
  disconnectText: {
    color: '#ff4d4f',
    fontSize: 16,
    fontWeight: '600',
  },
});