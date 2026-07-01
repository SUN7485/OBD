import React, { memo, useCallback } from 'react';
import { View, Text, StyleSheet, FlatList } from 'react-native';
import { useOBDStore } from '../store';

interface Gauge {
  id: string;
  name: string;
  value: number;
  max: number;
  unit: string;
  color: string;
}

const GAUGE_HEIGHT = 120;

function GaugeItem({ gauge }: { gauge: Gauge }) {
  return (
    <View style={styles.gaugeCard}>
      <View style={styles.gaugeHeader}>
        <Text style={styles.gaugeName}>{gauge.name}</Text>
        <Text style={[styles.gaugeValue, { color: gauge.color }]}>
          {gauge.value.toFixed(0)} {gauge.unit}
        </Text>
      </View>
      <View style={styles.gaugeBar}>
        <View
          style={[
            styles.gaugeFill,
            {
              width: `${Math.min((gauge.value / gauge.max) * 100, 100)}%`,
              backgroundColor: gauge.color,
            },
          ]}
        />
      </View>
      <View style={styles.gaugeLabels}>
        <Text style={styles.gaugeLabel}>0</Text>
        <Text style={styles.gaugeLabel}>{gauge.max}</Text>
      </View>
    </View>
  );
}

const MemoGaugeItem = memo(GaugeItem);

export default function GaugesScreen() {
  const { telemetry } = useOBDStore();

  const gauges: Gauge[] = [
    {
      id: 'speed',
      name: 'Speed',
      value: telemetry?.speed ?? 0,
      max: 200,
      unit: 'km/h',
      color: '#1890ff',
    },
    {
      id: 'rpm',
      name: 'RPM',
      value: telemetry?.rpm ?? 0,
      max: 8000,
      unit: 'rpm',
      color: '#52c41a',
    },
    {
      id: 'engineLoad',
      name: 'Engine Load',
      value: telemetry?.engineLoad ?? 0,
      max: 100,
      unit: '%',
      color: '#faad14',
    },
    {
      id: 'throttle',
      name: 'Throttle',
      value: telemetry?.throttle ?? 0,
      max: 100,
      unit: '%',
      color: '#722ed1',
    },
    {
      id: 'coolantTemp',
      name: 'Coolant Temp',
      value: telemetry?.coolantTemp ?? 0,
      max: 150,
      unit: '°C',
      color: '#ff4d4f',
    },
    {
      id: 'fuelLevel',
      name: 'Fuel Level',
      value: telemetry?.fuelLevel ?? 0,
      max: 100,
      unit: '%',
      color: '#13c2c2',
    },
  ];

  const renderGauge = useCallback(({ item }: { item: Gauge }) => (
    <MemoGaugeItem gauge={item} />
  ), []);

  const keyExtractor = useCallback((item: Gauge) => item.id, []);

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Live Gauges</Text>
      </View>
      <FlatList
        data={gauges}
        renderItem={renderGauge}
        keyExtractor={keyExtractor}
        contentContainerStyle={styles.list}
        getItemLayout={(_data, index) => ({
          length: GAUGE_HEIGHT,
          offset: GAUGE_HEIGHT * index,
          index,
        })}
      />
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
  list: {
    padding: 16,
  },
  gaugeCard: {
    backgroundColor: '#fff',
    marginBottom: 16,
    padding: 16,
    borderRadius: 12,
    height: GAUGE_HEIGHT - 16,
  },
  gaugeHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  gaugeName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
  },
  gaugeValue: {
    fontSize: 24,
    fontWeight: 'bold',
  },
  gaugeBar: {
    height: 12,
    backgroundColor: '#e0e0e0',
    borderRadius: 6,
    overflow: 'hidden',
  },
  gaugeFill: {
    height: '100%',
    borderRadius: 6,
  },
  gaugeLabels: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 4,
  },
  gaugeLabel: {
    fontSize: 12,
    color: '#999',
  },
});