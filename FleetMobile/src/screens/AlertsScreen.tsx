import React, { useEffect, useState, useCallback, memo } from 'react';
import { View, Text, StyleSheet, FlatList, RefreshControl } from 'react-native';
import { useAlertStore } from '../store';
import api from '../services/api';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';

interface AlertItem {
  id: string;
  severity: 'info' | 'warning' | 'critical';
  message: string;
  is_read: boolean;
  created_at: string;
}

function AlertCard({ item }: { item: AlertItem }) {
  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return '#ff4d4f';
      case 'warning': return '#faad14';
      default: return '#1890ff';
    }
  };

  return (
    <View style={[styles.alertCard, { borderLeftColor: getSeverityColor(item.severity) }]}>
      <View style={styles.alertHeader}>
        <Icon
          name={item.severity === 'critical' ? 'alert-circle' : 'information'}
          size={24}
          color={getSeverityColor(item.severity)}
        />
        <Text style={styles.alertSeverity}>{item.severity.toUpperCase()}</Text>
      </View>
      <Text style={styles.alertMessage}>{item.message}</Text>
      <Text style={styles.alertTime}>
        {new Date(item.created_at).toLocaleString()}
      </Text>
    </View>
  );
}

const MemoAlertCard = memo(AlertCard);

export default function AlertsScreen() {
  const { alerts, setAlerts } = useAlertStore();
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const fetchAlerts = useCallback(async () => {
    setLoading(true);
    try {
      const fetchedAlerts = await api.getAlerts();
      setAlerts(fetchedAlerts);
    } catch (error) {
      console.error('Failed to fetch alerts:', error);
    } finally {
      setLoading(false);
    }
  }, [setAlerts]);

  useEffect(() => {
    fetchAlerts();
  }, [fetchAlerts]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await fetchAlerts();
    setRefreshing(false);
  }, [fetchAlerts]);

  const renderAlert = useCallback(({ item }: { item: AlertItem }) => (
    <MemoAlertCard item={item} />
  ), []);

  const keyExtractor = useCallback((item: AlertItem) => item.id, []);

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Alerts</Text>
      </View>

      {alerts.length === 0 ? (
        <View style={styles.emptyState}>
          <Icon name="bell-off" size={64} color="#ccc" />
          <Text style={styles.emptyText}>No alerts</Text>
        </View>
      ) : (
        <FlatList
          data={alerts}
          renderItem={renderAlert}
          keyExtractor={keyExtractor}
          contentContainerStyle={styles.list}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
          }
        />
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
  list: {
    padding: 16,
  },
  alertCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    borderLeftWidth: 4,
  },
  alertHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  alertSeverity: {
    marginLeft: 8,
    fontSize: 12,
    fontWeight: '600',
    color: '#666',
  },
  alertMessage: {
    fontSize: 16,
    color: '#333',
    marginBottom: 8,
  },
  alertTime: {
    fontSize: 12,
    color: '#999',
  },
  emptyState: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  emptyText: {
    marginTop: 16,
    fontSize: 18,
    color: '#999',
  },
});