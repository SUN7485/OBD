import React, { useEffect, useState, useCallback } from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { View, Text, ActivityIndicator, StyleSheet, AppState, StatusBar } from 'react-native';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import { SafeAreaProvider, useSafeAreaInsets } from 'react-native-safe-area-context';

import { useAuthStore } from './src/store';
import api, { initializeApiUrl } from './src/services/api';
import MQTTPublisher from './src/services/MQTTPublisher';
import AlertWebSocket from './src/services/AlertWebSocket';
import ErrorBoundary from './src/components/ErrorBoundary';
import TelemetryStreamer from './src/services/TelemetryStreamer';

import LoginScreen from './src/screens/LoginScreen';
import DashboardScreen from './src/screens/DashboardScreen';
import GaugesScreen from './src/screens/GaugesScreen';
import DiagnosticsScreen from './src/screens/DiagnosticsScreen';
import AlertsScreen from './src/screens/AlertsScreen';
import SettingsScreen from './src/screens/SettingsScreen';
import BLEConnectScreen from './src/screens/BLEConnectScreen';

const Stack = createNativeStackNavigator();
const Tab = createBottomTabNavigator();

function DashboardTabs() {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        tabBarIcon: ({ focused, color, size }) => {
          let iconName = 'car';
          if (route.name === 'Dashboard') iconName = 'view-dashboard';
          else if (route.name === 'Gauges') iconName = 'gauge';
          else if (route.name === 'Diagnostics') iconName = 'stethoscope';
          else if (route.name === 'Alerts') iconName = 'bell';
          else if (route.name === 'Settings') iconName = 'cog';
          return <Icon name={iconName} size={size} color={color} />;
        },
        tabBarActiveTintColor: '#1890ff',
        tabBarInactiveTintColor: 'gray',
        headerShown: false,
        tabBarStyle: {
          height: 56,
        },
        tabBarLabelStyle: {
          fontSize: 12,
        },
      })}
    >
      <Tab.Screen name="Dashboard" component={DashboardScreen} />
      <Tab.Screen name="Gauges" component={GaugesScreen} />
      <Tab.Screen name="Diagnostics" component={DiagnosticsScreen} />
      <Tab.Screen name="Alerts" component={AlertsScreen} />
      <Tab.Screen name="Settings" component={SettingsScreen} />
    </Tab.Navigator>
  );
}

function AppInner() {
  const { isAuthenticated, checkAuth, user } = useAuthStore();
  const [loading, setLoading] = useState(true);
  const insets = useSafeAreaInsets();

  useEffect(() => {
    const initialize = async () => {
      try {
        await initializeApiUrl();

        const hasAuth = await checkAuth();
        if (hasAuth && user) {
          const token = await api.getToken();
          const host = api.getHost();
          if (token && host && !host.includes('undefined')) {
            AlertWebSocket.setToken(token);
            AlertWebSocket.connect(host);
          }
        }
      } catch (e) {
        console.error('AppInner init failed:', e);
      } finally {
        setLoading(false);
      }
    };
    initialize();

    const handleAppStateChange = (state: string) => {
      if (state === 'active') {
        MQTTPublisher.connect().catch((e) => console.error('MQTTPublisher.connect failed:', e));
        TelemetryStreamer.start().catch((e) => console.error('TelemetryStreamer.start failed:', e));
      } else {
        TelemetryStreamer.stop();
      }
    };

    const subscription = AppState.addEventListener('change', handleAppStateChange);
    return () => {
      subscription.remove();
      TelemetryStreamer.destroy();
      MQTTPublisher.disconnect();
      AlertWebSocket.disconnect();
    };
  }, []);

  if (loading) {
    return (
      <View style={[styles.loading, { paddingTop: insets.top }]}>
        <ActivityIndicator size="large" color="#ff6b35" />
        <Text style={styles.loadingText}>Loading Fleet OBD...</Text>
      </View>
    );
  }

  return (
    <>
      <StatusBar barStyle="light-content" backgroundColor="#0b1220" />
      <NavigationContainer>
        <Stack.Navigator screenOptions={{ headerShown: false }}>
          {!isAuthenticated ? (
            <Stack.Screen name="Login" component={LoginScreen} />
          ) : (
            <>
              <Stack.Screen name="Main" component={DashboardTabs} />
              <Stack.Screen
                name="BLEConnect"
                component={BLEConnectScreen}
                options={{ headerShown: true, title: 'Connect to OBD' }}
              />
            </>
          )}
        </Stack.Navigator>
      </NavigationContainer>
    </>
  );
}

export default function App() {
  return (
    <SafeAreaProvider>
      <ErrorBoundary>
        <AppInner />
      </ErrorBoundary>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  loading: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#001529',
  },
  loadingText: {
    marginTop: 16,
    fontSize: 16,
    color: '#a0a0a0',
  },
});