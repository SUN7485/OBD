import React, { useCallback, memo } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, FlatList } from 'react-native';
import { useOBDStore, useAlertStore } from '../store';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';

interface Metric {
  id: string;
  label: string;
  value: number | string;
  unit: string;
  icon: string;
}

function MetricCard({ metric }: { metric: Metric }) {
  return (
    <View style={styles.metricCard}>
      <Icon name={metric.icon} size={32} color="#1890ff" />
      <Text style={styles.metricValue}>{metric.value}</Text>
      <Text style={styles.metricLabel}>{metric.label}</Text>
      <Text style={styles.metricUnit}>{metric.unit}</Text>
    </View>
  );
}

const MemoMetricCard = memo(MetricCard);

function ActionButton({ icon, label, onPress, color = '#1890ff' }: {
  icon: string;
  label: string;
  onPress: () => void;
  color?: string;
}) {
  return (
    <TouchableOpacity style={styles.actionButton} onPress={onPress}>
      <Icon name={icon} size={32} color={color} />
      <Text style={styles.actionText}>{label}</Text>
    </TouchableOpacity>
  );
}

export default function DashboardScreen({ navigation }: { navigation: any }) {
  const { isConnected, telemetry } = useOBDStore();
  const { unreadCount } = useAlertStore();

  const metrics: Metric[] = [
    { id: 'speed', label: 'Speed', value: telemetry?.speed?.toFixed(0) ?? 0, unit: 'km/h', icon: 'speedometer' },
    { id: 'rpm', label: 'RPM', value: telemetry?.rpm?.toFixed(0) ?? 0, unit: '', icon: 'engine' },
    { id: 'fuel', label: 'Fuel', value: telemetry?.fuel_level?.toFixed(0) ?? 0, unit: '%', icon: 'gas-station' },
    { id: 'temp', label: 'Temp', value: telemetry?.coolant_temp?.toFixed(0) ?? 0, unit: '°C', icon: 'thermometer' },
  ];

  const renderMetric = useCallback(({ item }: { item: Metric }) => (
    <MemoMetricCard metric={item} />
  ), []);

  const keyExtractor = useCallback((item: Metric) => item.id, []);

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>My Vehicle</Text>
        <TouchableOpacity
          onPress={() => navigation.navigate('BLEConnect')}
          style={styles.headerButton}
        >
          <Icon
            name={isConnected ? 'bluetooth-connect' : 'bluetooth-off'}
            size={24}
            color={isConnected ? '#52c41a' : '#999'}
          />
        </TouchableOpacity>
      </View>

      <View style={[styles.connectionStatus, isConnected ? styles.connected : styles.disconnected]}>
        <Icon
          name={isConnected ? 'check-circle' : 'alert-circle'}
          size={20}
          color="#fff"
        />
        <Text style={styles.statusText}>
          {isConnected ? 'OBD Connected' : 'Not Connected'}
        </Text>
      </View>

      <FlatList
        data={metrics}
        renderItem={renderMetric}
        keyExtractor={keyExtractor}
        numColumns={2}
        columnWrapperStyle={styles.metricsRow}
        contentContainerStyle={styles.metricsContainer}
        scrollEnabled={false}
      />

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Quick Actions</Text>
        <View style={styles.actionsGrid}>
          <ActionButton
            icon="gauge"
            label="Live Gauges"
            color="#1890ff"
            onPress={() => navigation.navigate('Gauges')}
          />
          <ActionButton
            icon="stethoscope"
            label="Diagnostics"
            color="#52c41a"
            onPress={() => navigation.navigate('Diagnostics')}
          />
          <ActionButton
            icon="bell"
            label={`Alerts (${unreadCount})`}
            color="#faad14"
            onPress={() => navigation.navigate('Alerts')}
          />
          <ActionButton
            icon="cog"
            label="Settings"
            color="#666"
            onPress={() => navigation.navigate('Settings')}
          />
        </View>
      </View>

      <View style={styles.infoCard}>
        <Icon name="information" size={24} color="#1890ff" />
        <Text style={styles.infoText}>
          Connect your OBD device to start receiving real-time vehicle data
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f6fa',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 16,
    backgroundColor: '#0b1220',
    minHeight: 56,
  },
  headerButton: {
    padding: 8,
    minWidth: 44,
    minHeight: 44,
    alignItems: 'center',
    justifyContent: 'center',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#fff',
  },
  connectionStatus: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 12,
    margin: 16,
    borderRadius: 8,
  },
  connected: {
    backgroundColor: '#52c41a',
  },
  disconnected: {
    backgroundColor: '#faad14',
  },
  statusText: {
    color: '#fff',
    marginLeft: 8,
    fontSize: 16,
    fontWeight: '600',
  },
  metricsContainer: {
    paddingHorizontal: 8,
  },
  metricsRow: {
    justifyContent: 'space-between',
  },
  metricCard: {
    width: '48%',
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    margin: '1%',
    alignItems: 'center',
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
  },
  metricValue: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#333',
    marginTop: 8,
  },
  metricLabel: {
    fontSize: 14,
    color: '#666',
  },
  metricUnit: {
    fontSize: 12,
    color: '#999',
  },
  section: {
    padding: 16,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 12,
    color: '#333',
  },
  actionsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  actionButton: {
    width: '48%',
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 20,
    marginBottom: 12,
    alignItems: 'center',
    elevation: 2,
    minHeight: 72,
    justifyContent: 'center',
  },
  actionText: {
    marginTop: 8,
    fontSize: 14,
    color: '#333',
  },
  infoCard: {
    flexDirection: 'row',
    backgroundColor: '#e6f7ff',
    margin: 16,
    padding: 16,
    borderRadius: 8,
    alignItems: 'center',
  },
  infoText: {
    flex: 1,
    marginLeft: 12,
    color: '#1890ff',
  },
});