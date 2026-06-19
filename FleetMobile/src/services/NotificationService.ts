/**
 * Notification Service - In-app notifications for alerts
 */

import { Alert } from 'react-native';

interface AlertNotification {
  id: string;
  title: string;
  body: string;
  severity: 'info' | 'warning' | 'critical';
  data?: Record<string, unknown>;
}

class NotificationService {
  async displayAlert(alert: AlertNotification): Promise<void> {
    const severityTitles = {
      info: 'Information',
      warning: 'Warning',
      critical: 'Critical Alert',
    };

    Alert.alert(
      `${severityTitles[alert.severity]}: ${alert.title}`,
      alert.body,
      [{ text: 'OK', style: 'default' }]
    );
  }

  async cancelNotification(id: string): Promise<void> {
    console.log('Notification cancelled:', id);
  }

  async cancelAllNotifications(): Promise<void> {
    console.log('All notifications cancelled');
  }
}

export default new NotificationService();