import React, { useState, useCallback, memo } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Alert, FlatList } from 'react-native';
import { useOBDStore } from '../store';
import api from '../services/api';
import OBDManager from '../services/OBDManager';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';

interface DTCCardProps {
  code: string;
  onExplain: () => void;
}

function DTCCard({ code, onExplain }: DTCCardProps) {
  const dtcDescriptions: Record<string, string> = {
    'P0171': 'System Too Lean (Bank 1) - Check for vacuum leaks',
    'P0420': 'Catalyst System Efficiency Below Threshold',
    'P0300': 'Random/Multiple Cylinder Misfire Detected',
    'P0128': 'Coolant Thermostat Temperature Below Regulating',
  };

  return (
    <View style={styles.dtcCard}>
      <View style={styles.dtcHeader}>
        <Text style={styles.dtcCode}>{code}</Text>
        <TouchableOpacity onPress={onExplain} style={styles.explainButton}>
          <Icon name="robot" size={24} color="#1890ff" />
        </TouchableOpacity>
      </View>
      <Text style={styles.dtcDescription}>
        {dtcDescriptions[code] || 'Unknown code'}
      </Text>
    </View>
  );
}

const MemoDTCCard = memo(DTCCard);

export default function DiagnosticsScreen() {
  const { dtcCodes, setDTCCodes, isConnected } = useOBDStore();
  const [loading, setLoading] = useState(false);
  const [aiResponse, setAiResponse] = useState<string | null>(null);

  const readDTCs = useCallback(async () => {
    if (!isConnected) {
      Alert.alert('Not Connected', 'Please connect to OBD device first');
      return;
    }
    setLoading(true);
    try {
      const codes = await OBDManager.readDTCs();
      setDTCCodes(codes);
      Alert.alert('Success', `Found ${codes.length} trouble codes`);
    } catch (error) {
      Alert.alert('Error', 'Failed to read DTCs');
    } finally {
      setLoading(false);
    }
  }, [isConnected, setDTCCodes]);

  const clearDTCs = useCallback(() => {
    if (!isConnected) {
      Alert.alert('Not Connected', 'Please connect to OBD device first');
      return;
    }
    Alert.alert(
      'Clear DTCs',
      'Are you sure you want to clear diagnostic trouble codes?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Clear',
          style: 'destructive',
          onPress: async () => {
            try {
              await OBDManager.clearDTCs();
              setDTCCodes([]);
              Alert.alert('Success', 'DTCs cleared');
            } catch {
              Alert.alert('Error', 'Failed to clear DTCs');
            }
          },
        },
      ]
    );
  }, [isConnected, setDTCCodes]);

  const explainDTC = useCallback(async (code: string) => {
    setLoading(true);
    try {
      const response = await api.explainDTC(code);
      setAiResponse(response.message);
    } catch (error) {
      setAiResponse('Unable to get explanation. Please check connection.');
    } finally {
      setLoading(false);
    }
  }, []);

  const renderDTC = useCallback(({ item }: { item: string }) => (
    <MemoDTCCard code={item} onExplain={() => explainDTC(item)} />
  ), [explainDTC]);

  const keyExtractor = useCallback((item: string) => item, []);

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Diagnostics</Text>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Trouble Codes (DTCs)</Text>

        <View style={styles.buttonRow}>
          <TouchableOpacity
            style={[styles.button, loading && styles.buttonDisabled]}
            onPress={readDTCs}
            disabled={loading}
          >
            <Icon name="magnify" size={24} color="#fff" />
            <Text style={styles.buttonText}>Scan Codes</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.button, styles.destructiveButton]}
            onPress={clearDTCs}
          >
            <Icon name="delete" size={24} color="#fff" />
            <Text style={styles.buttonText}>Clear</Text>
          </TouchableOpacity>
        </View>

        {dtcCodes.length === 0 ? (
          <View style={styles.emptyState}>
            <Icon name="check-circle" size={48} color="#52c41a" />
            <Text style={styles.emptyText}>No trouble codes found</Text>
          </View>
        ) : (
          <FlatList
            data={dtcCodes}
            renderItem={renderDTC}
            keyExtractor={keyExtractor}
            contentContainerStyle={styles.dtcList}
          />
        )}
      </View>

      {aiResponse && (
        <View style={styles.aiSection}>
          <Text style={styles.sectionTitle}>AI Explanation</Text>
          <View style={styles.aiCard}>
            <Icon name="robot-happy" size={32} color="#1890ff" />
            <Text style={styles.aiText}>{aiResponse}</Text>
          </View>
        </View>
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
  section: {
    padding: 16,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 12,
    color: '#333',
  },
  buttonRow: {
    flexDirection: 'row',
    marginBottom: 16,
  },
  button: {
    flex: 1,
    flexDirection: 'row',
    backgroundColor: '#1890ff',
    borderRadius: 8,
    padding: 12,
    marginRight: 8,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 48,
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  destructiveButton: {
    backgroundColor: '#ff4d4f',
    marginRight: 0,
    marginLeft: 8,
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
    marginLeft: 8,
  },
  emptyState: {
    alignItems: 'center',
    padding: 32,
    backgroundColor: '#fff',
    borderRadius: 12,
  },
  emptyText: {
    marginTop: 12,
    color: '#666',
    fontSize: 16,
  },
  dtcList: {
    marginTop: 8,
  },
  dtcCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    borderLeftWidth: 4,
    borderLeftColor: '#faad14',
  },
  dtcHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  dtcCode: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#333',
  },
  explainButton: {
    padding: 8,
    minWidth: 44,
  },
  dtcDescription: {
    color: '#666',
    fontSize: 14,
  },
  aiSection: {
    padding: 16,
    paddingTop: 0,
  },
  aiCard: {
    backgroundColor: '#e6f7ff',
    borderRadius: 12,
    padding: 16,
    flexDirection: 'row',
  },
  aiText: {
    flex: 1,
    marginLeft: 12,
    color: '#333',
  },
});