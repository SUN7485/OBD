'use client'

import { useEffect, useState } from 'react'
import { Row, Col, Card, Statistic, Table, Tag, Progress, Space, Typography, Spin, Empty, Result, Button } from 'antd'
import {
  CarOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  ClockCircleOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  DashboardOutlined,
} from '@ant-design/icons'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
} from 'recharts'
import { analyticsAPI, carsAPI, alertsAPI } from '@/lib/api'
import { useFleetStore, useTelemetryStore, useAlertStore } from '@/lib/store'

const { Title, Text } = Typography

interface FleetSummary {
  total_cars: number
  active_cars: number
  total_distance_km: number
  total_fuel_l: number
  alerts_by_severity: { info: number; warning: number; critical: number }
  hourly_activity?: { hour: string; avg_speed: number; avg_rpm: number }[]
}

export default function DashboardPage() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [summary, setSummary] = useState<FleetSummary | null>(null)
  const { cars, setCars } = useFleetStore()
  const { liveData } = useTelemetryStore()
  const { alerts, setAlerts } = useAlertStore()

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      setError(null)
      const [summaryRes, carsRes, alertsRes] = await Promise.all([
        analyticsAPI.fleetSummary().catch(() => ({ data: null })),
        carsAPI.list().catch(() => ({ data: [] })),
        alertsAPI.list({ limit: 10 }).catch(() => ({ data: [] })),
      ])

      if (summaryRes.data) setSummary(summaryRes.data)
      if (carsRes.data) setCars(carsRes.data)
      if (alertsRes.data) setAlerts(alertsRes.data)
    } catch (err) {
      console.error('Failed to load dashboard data:', err)
      setError('Failed to load dashboard data')
    } finally {
      setLoading(false)
    }
  }

  const recentAlerts = alerts.slice(0, 5)

  const getHourlyActivity = () => {
    if (!summary?.hourly_activity) return []
    return summary.hourly_activity.map((item: any) => ({
      time: new Date(item.hour).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
      speed: item.avg_speed || 0,
      rpm: item.avg_rpm || 0,
    }))
  }

  const chartData = getHourlyActivity()

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 400 }}>
        <Spin size="large" />
      </div>
    )
  }

  if (error) {
    return (
      <div>
        <div style={{ marginBottom: 24 }}>
          <Title level={2} style={{ margin: 0 }}>
            <DashboardOutlined /> Fleet Dashboard
          </Title>
          <Text type="secondary">Real-time overview of your fleet</Text>
        </div>
        <Result
          status="error"
          title="Failed to load dashboard"
          subTitle={error}
          extra={
            <Button type="primary" onClick={loadData}>
              Retry
            </Button>
          }
        />
      </div>
    )
  }

  if (!summary && cars.length === 0) {
    return (
      <div>
        <div style={{ marginBottom: 24 }}>
          <Title level={2} style={{ margin: 0 }}>
            <DashboardOutlined /> Fleet Dashboard
          </Title>
          <Text type="secondary">Real-time overview of your fleet</Text>
        </div>
        <Card>
          <Empty
            description="No fleet data available. Add your first vehicle to get started."
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          />
        </Card>
      </div>
    )
  }

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <Title level={2} style={{ margin: 0 }}>
          <DashboardOutlined /> Fleet Dashboard
        </Title>
        <Text type="secondary">Real-time overview of your fleet</Text>
      </div>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Total Vehicles"
              value={summary?.total_cars || cars.length || 0}
              prefix={<CarOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Active Now"
              value={summary?.active_cars || Object.keys(liveData).length}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Total Distance (km)"
              value={summary?.total_distance_km || 0}
              precision={1}
              prefix={<ArrowUpOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Active Alerts"
              value={(summary?.alerts_by_severity?.warning || 0) + 
                     (summary?.alerts_by_severity?.critical || 0)}
              prefix={<WarningOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Charts */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} lg={16}>
          <Card title="Fleet Activity (Last 24h)">
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={chartData.length > 0 ? chartData : [
    { time: '00:00', speed: 0, rpm: 0 },
    { time: '06:00', speed: 0, rpm: 0 },
    { time: '12:00', speed: 0, rpm: 0 },
    { time: '18:00', speed: 0, rpm: 0 },
  ]}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="time" />
                <YAxis yAxisId="left" />
                <YAxis yAxisId="right" orientation="right" />
                <Tooltip />
                <Area
                  yAxisId="left"
                  type="monotone"
                  dataKey="speed"
                  stroke="#1890ff"
                  fill="#1890ff"
                  fillOpacity={0.3}
                  name="Speed (km/h)"
                />
                <Area
                  yAxisId="right"
                  type="monotone"
                  dataKey="rpm"
                  stroke="#52c41a"
                  fill="#52c41a"
                  fillOpacity={0.3}
                  name="RPM"
                />
              </AreaChart>
            </ResponsiveContainer>
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title="Alert Severity">
            <Space direction="vertical" style={{ width: '100%' }} size="large">
              <div>
                <Text>Critical</Text>
                <Progress 
                  percent={summary?.alerts_by_severity?.critical || 0} 
                  status="exception" 
                  strokeColor="#ff4d4f"
                />
              </div>
              <div>
                <Text>Warning</Text>
                <Progress 
                  percent={summary?.alerts_by_severity?.warning || 0} 
                  status="active"
                  strokeColor="#faad14"
                />
              </div>
              <div>
                <Text>Info</Text>
                <Progress 
                  percent={summary?.alerts_by_severity?.info || 0} 
                  strokeColor="#1890ff"
                />
              </div>
            </Space>
          </Card>
        </Col>
      </Row>

      {/* Live Vehicles & Alerts */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card 
            title="Live Vehicles" 
            extra={<Tag color="green">{Object.keys(liveData).length} Online</Tag>}
          >
            <Table
              size="small"
              dataSource={cars.slice(0, 5)}
              rowKey="id"
              pagination={false}
              columns={[
                { 
                  title: 'Vehicle', 
                  dataIndex: 'name',
                  render: (name, record) => (
                    <Space>
                      <CarOutlined />
                      <div>
                        <div>{name}</div>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {record.license_plate}
                        </Text>
                      </div>
                    </Space>
                  )
                },
                { 
                  title: 'Speed', 
                  dataIndex: 'id',
                  render: (id) => liveData[id]?.speed?.toFixed(0) + ' km/h' || '-'
                },
                { 
                  title: 'Status', 
                  dataIndex: 'status',
                  render: (status) => (
                    <Tag color={status === 'online' ? 'green' : 'default'}>
                      {status || 'offline'}
                    </Tag>
                  )
                },
              ]}
            />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card 
            title="Recent Alerts" 
            extra={<a href="/dashboard/alerts">View All</a>}
          >
            <Table
              size="small"
              dataSource={recentAlerts}
              rowKey="id"
              pagination={false}
              columns={[
                {
                  title: 'Severity',
                  dataIndex: 'severity',
                  render: (severity) => (
                    <Tag color={
                      severity === 'critical' ? 'red' : 
                      severity === 'warning' ? 'orange' : 'blue'
                    }>
                      {severity}
                    </Tag>
                  )
                },
                { title: 'Message', dataIndex: 'message', ellipsis: true },
                { 
                  title: 'Time', 
                  dataIndex: 'created_at',
                  render: (time) => (
                    <Text type="secondary">
                      <ClockCircleOutlined /> {new Date(time).toLocaleTimeString()}
                    </Text>
                  )
                },
              ]}
            />
          </Card>
        </Col>
      </Row>
    </div>
  )
}
