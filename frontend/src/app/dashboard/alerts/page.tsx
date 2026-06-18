'use client'

import { useEffect, useState } from 'react'
import { 
  Card, Table, Tag, Button, Space, Select, Typography, 
  Badge, Modal, message, Tabs, Empty 
} from 'antd'
import { 
  BellOutlined, CheckCircleOutlined, ClockCircleOutlined,
  ExclamationCircleOutlined, CheckOutlined 
} from '@ant-design/icons'
import { alertsAPI } from '@/lib/api'
import { useAlertStore } from '@/lib/store'

const { Title, Text } = Typography
const { Option } = Select

interface Alert {
  id: string
  car_id: string
  car_name?: string
  severity: 'info' | 'warning' | 'critical'
  message: string
  is_read: boolean
  is_resolved: boolean
  created_at: string
  resolved_at?: string
}

export default function AlertsPage() {
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState('all')
  const { alerts, setAlerts, markRead } = useAlertStore()

  useEffect(() => {
    loadAlerts()
  }, [filter])

  const loadAlerts = async () => {
    try {
      setLoading(true)
      const params: any = { limit: 100 }
      if (filter) params.severity = filter
      const response = await alertsAPI.list(params)
      setAlerts(response.data || [])
    } catch (error) {
      console.error('Failed to load alerts:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleMarkRead = async (id: string) => {
    try {
      await alertsAPI.markRead(id)
      markRead(id)
      message.success('Alert marked as read')
    } catch (error) {
      message.error('Failed to mark alert')
    }
  }

  const handleResolve = async (id: string) => {
    try {
      await alertsAPI.resolve(id)
      message.success('Alert resolved')
      loadAlerts()
    } catch (error) {
      message.error('Failed to resolve alert')
    }
  }

  const getFilteredAlerts = () => {
    switch (activeTab) {
      case 'unread':
        return alerts.filter(a => !a.is_read)
      case 'resolved':
        return alerts.filter(a => a.is_resolved)
      default:
        return alerts
    }
  }

  const columns = [
    {
      title: 'Severity',
      dataIndex: 'severity',
      width: 100,
      render: (severity: string) => (
        <Tag color={
          severity === 'critical' ? 'red' : 
          severity === 'warning' ? 'orange' : 'blue'
        }>
          {severity?.toUpperCase()}
        </Tag>
      ),
    },
    {
      title: 'Vehicle',
      dataIndex: 'car_name',
      render: (name: string, record: Alert) => name || record.car_id,
    },
    {
      title: 'Message',
      dataIndex: 'message',
      ellipsis: true,
    },
    {
      title: 'Time',
      dataIndex: 'created_at',
      width: 150,
      render: (time: string) => (
        <Text type="secondary">
          <ClockCircleOutlined /> {new Date(time).toLocaleString()}
        </Text>
      ),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      width: 120,
      render: (_: any, record: Alert) => (
        <Space>
          {!record.is_read && (
            <Button 
              type="link" 
              size="small" 
              icon={<CheckOutlined />}
              onClick={() => handleMarkRead(record.id)}
            >
              Mark Read
            </Button>
          )}
          {!record.is_resolved && (
            <Button 
              type="link" 
              size="small" 
              icon={<CheckCircleOutlined />}
              onClick={() => handleResolve(record.id)}
            >
              Resolve
            </Button>
          )}
        </Space>
      ),
    },
  ]

  const alertStats = {
    critical: alerts.filter(a => a.severity === 'critical' && !a.is_resolved).length,
    warning: alerts.filter(a => a.severity === 'warning' && !a.is_resolved).length,
    unread: alerts.filter(a => !a.is_read).length,
  }

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <Title level={2} style={{ margin: 0 }}>
          <BellOutlined /> Alerts
        </Title>
        <Text type="secondary">Monitor fleet alerts and notifications</Text>
      </div>

      {/* Alert Stats */}
      <Space size="large" style={{ marginBottom: 24 }}>
        <Card size="small">
          <Badge count={alertStats.critical} overflowCount={99}>
            <Tag color="red">CRITICAL</Tag>
          </Badge>
        </Card>
        <Card size="small">
          <Badge count={alertStats.warning} overflowCount={99}>
            <Tag color="orange">WARNING</Tag>
          </Badge>
        </Card>
        <Card size="small">
          <Badge count={alertStats.unread} overflowCount={99}>
            <Tag color="blue">UNREAD</Tag>
          </Badge>
        </Card>
      </Space>

      <Card>
        <Tabs 
          activeKey={activeTab} 
          onChange={setActiveTab}
          items={[
            { key: 'all', label: 'All' },
            { key: 'unread', label: 'Unread' },
            { key: 'resolved', label: 'Resolved' },
          ]}
        />
        <Space style={{ marginBottom: 16 }}>
          <Select
            placeholder="Filter by severity"
            allowClear
            style={{ width: 200 }}
            value={filter}
            onChange={setFilter}
          >
            <Option value="critical">Critical</Option>
            <Option value="warning">Warning</Option>
            <Option value="info">Info</Option>
          </Select>
        </Space>

        <Table
          dataSource={getFilteredAlerts()}
          columns={columns}
          rowKey="id"
          loading={loading}
          locale={{ emptyText: <Empty description="No alerts" /> }}
        />
      </Card>
    </div>
  )
}
