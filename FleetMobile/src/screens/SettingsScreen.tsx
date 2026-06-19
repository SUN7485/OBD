import React, { useCallback, memo } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Switch, Alert, FlatList } from 'react-native';
import { useAuthStore, useOBDStore } from '../store';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';

interface SettingItem {
  icon: string;
  label: string;
  value?: string | boolean;
  onPress?: () => void;
  danger?: boolean;
}

interface SettingSection {
  title: string;
  items: SettingItem[];
}

function SettingRow({ item }: { item: SettingItem }) {
  return (
    <TouchableOpacity
      style={styles.settingItem}
      onPress={item.onPress}
      disabled={!item.onPress}
    >
      <Icon
        name={item.icon as any}
        size={24}
        color={item.danger ? '#ff4d4f' : '#666'}
      />
      <Text style={[styles.settingLabel, item.danger && styles.dangerText]}>
        {item.label}
      </Text>
      {item.onPress ? (
        <Text style={styles.settingValue}>{item.value as string}</Text>
      ) : (
        <Switch value={item.value as boolean} />
      )}
    </TouchableOpacity>
  );
}

const MemoSettingRow = memo(SettingRow);

export default function SettingsScreen({ navigation }: { navigation: any }) {
  const { user, logout } = useAuthStore();
  const { isConnected, connectedDevice, setDisconnected } = useOBDStore();

  const handleLogout = useCallback(() => {
    Alert.alert(
      'Logout',
      'Are you sure you want to logout?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Logout',
          style: 'destructive',
          onPress: () => {
            logout();
            if (isConnected) setDisconnected();
          },
        },
      ]
    );
  }, [logout, isConnected, setDisconnected]);

  const settings: SettingSection[] = [
    {
      title: 'OBD Connection',
      items: [
        {
          icon: 'bluetooth',
          label: 'Bluetooth Device',
          value: connectedDevice || 'Not connected',
          onPress: () => navigation.navigate('BLEConnect'),
        },
        {
          icon: 'wifi',
          label: 'Auto Reconnect',
          value: true,
        },
      ],
    },
    {
      title: 'Data & Sync',
      items: [
        {
          icon: 'cloud-upload',
          label: 'Upload Data',
          value: 'Always',
        },
        {
          icon: 'sync',
          label: 'Sync Interval',
          value: '1 min',
        },
      ],
    },
    {
      title: 'Notifications',
      items: [
        {
          icon: 'bell',
          label: 'Push Notifications',
          value: true,
        },
        {
          icon: 'alert',
          label: 'Critical Alerts',
          value: true,
        },
      ],
    },
    {
      title: 'Account',
      items: [
        {
          icon: 'account',
          label: 'Email',
          value: user?.email || 'user@example.com',
        },
        {
          icon: 'logout',
          label: 'Logout',
          onPress: handleLogout,
          danger: true,
        },
      ],
    },
  ];

  const renderSetting = useCallback(({ item }: { item: SettingItem }) => (
    <MemoSettingRow item={item} />
  ), []);

  const keyExtractor = useCallback((item: SettingItem, index: number) => `${item.label}_${index}`, []);

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Settings</Text>
      </View>

      <View style={styles.userCard}>
        <View style={styles.avatar}>
          <Icon name="account" size={32} color="#fff" />
        </View>
        <View style={styles.userInfo}>
          <Text style={styles.userName}>{user?.email}</Text>
          <Text style={styles.userOrg}>{user?.organization_name}</Text>
        </View>
      </View>

      {settings.map((section) => (
        <View key={section.title} style={styles.section}>
          <Text style={styles.sectionTitle}>{section.title}</Text>
          <View style={styles.sectionContent}>
            <FlatList
              data={section.items}
              renderItem={renderSetting}
              keyExtractor={keyExtractor}
              scrollEnabled={false}
            />
          </View>
        </View>
      ))}

      <Text style={styles.version}>Fleet OBD Mobile v1.0.0</Text>
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
  userCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    margin: 16,
    padding: 16,
    borderRadius: 12,
  },
  avatar: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: '#1890ff',
    alignItems: 'center',
    justifyContent: 'center',
    minWidth: 56,
    minHeight: 56,
  },
  userInfo: {
    marginLeft: 16,
    flex: 1,
  },
  userName: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
  },
  userOrg: {
    fontSize: 14,
    color: '#666',
  },
  section: {
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#999',
    marginLeft: 16,
    marginBottom: 8,
    textTransform: 'uppercase',
  },
  sectionContent: {
    backgroundColor: '#fff',
    marginHorizontal: 16,
    borderRadius: 12,
  },
  settingItem: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    minHeight: 56,
  },
  settingLabel: {
    flex: 1,
    marginLeft: 12,
    fontSize: 16,
    color: '#333',
  },
  dangerText: {
    color: '#ff4d4f',
  },
  settingValue: {
    color: '#999',
  },
  version: {
    textAlign: 'center',
    color: '#999',
    marginTop: 16,
    marginBottom: 32,
  },
});