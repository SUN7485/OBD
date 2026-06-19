'use client'

import { useEffect, useState, useMemo } from 'react'
import { 
  Card, Table, Tag, Button, Space, Select, Typography, 
  Badge, Modal, message, Tabs, Empty, Row, Col 
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
      setAlerts(response.data?.alerts || [])
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

  const getFilteredAlerts = useMemo(() => {
    switch (activeTab) {
      case 'unread':
        return alerts.filter(a => !a.is_read)
      case 'resolved':
        return alerts.filter(a => a.is_resolved)
      default:
        return alerts
    }
  }, [alerts, activeTab])

  const columns = [
    {
      title: 'Severity',
      dataIndex: 'severity',
      width: 100,
      render: (severity: string) => (
        <Tag style={{ borderRadius: 20, fontWeight: 600 }} color={
          severity === 'critical' ? 'error' : 
          severity === 'warning' ? 'warning' : 'processing'
        }>
          {severity?.toUpperCase()}
        </Tag>
      ),
    },
    {
      title: 'Vehicle',
      dataIndex: 'car_id',
    },
    {
      title: 'Message',
      dataIndex: 'message',
      ellipsis: true,
    },
    {
      title: 'Time',
      dataIndex: 'created_at',
      width: 180,
      render: (time: string) => (
        <Text type="secondary" style={{ color: '#64748b' }}>
          <ClockCircleOutlined style={{ marginRight: 4 }} />
          {new Date(time).toLocaleString()}
        </Text>
      ),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      width: 180,
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

  const alertStats = useMemo(() => ({
    critical: alerts.filter(a => a.severity === 'critical' && !a.is_resolved).length,
    warning: alerts.filter(a => a.severity === 'warning' && !a.is_resolved).length,
    unread: alerts.filter(a => !a.is_read).length,
  }), [alerts])

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <Title level={2} style={{ margin: 0, fontWeight: 800 }}>
          <BellOutlined style={{ color: '#faad14' }} /> Alerts
        </Title>
        <Text type="secondary">Monitor fleet alerts and notifications</Text>
      </div>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={8}>
          <Card size="small" style={{ borderRadius: 10, border: '1px solid #fff1f0', background: '#fff1f0' }}>
            <Space>
              <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#ff4d4f' }} />
              <Text strong>CRITICAL</Text>
            </Space>
            <Text style={{ fontSize: 24, fontWeight: 800, color: '#ff4d4f', lineHeight: 1, display: 'block', marginTop: 4 }}>
              {alertStats.critical}
            </Text>
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card size="small" style={{ borderRadius: 10, border: '1px solid #fffbe6', background: '#fffbe6' }}>
            <Space>
              <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#faad14' }} />
              <Text strong>WARNING</Text>
            </Space>
            <Text style={{ fontSize: 24, fontWeight: 800, color: '#d46b08', lineHeight: 1, display: 'block', marginTop: 4 }}>
              {alertStats.warning}
            </Text>
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card size="small" style={{ borderRadius: 10, border: '1px solid #e6f7ff', background: '#e6f7ff' }}>
            <Space>
              <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#1890ff' }} />
              <Text strong>UNREAD</Text>
            </Space>
            <Text style={{ fontSize: 24, fontWeight: 800, color: '#1677ff', lineHeight: 1, display: 'block', marginTop: 4 }}>
              {alertStats.unread}
            </Text>
          </Card>
        </Col>
      </Row>

      <Card style={{ borderRadius: 12, border: '1px solid #e8ecf1' }}>
        <Tabs 
          activeKey={activeTab} 
          onChange={setActiveTab}
          style={{ marginBottom: 16 }}
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
          dataSource={getFilteredAlerts}
          columns={columns}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 20 }}
          locale={{ emptyText: <Empty description="No alerts" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
        />
      </Card>
    </div>
  )
}
