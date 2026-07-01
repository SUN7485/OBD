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
  AlertOutlined,
  ToolOutlined,
  FireOutlined,
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
  total_fuel_consumed_l?: number
  total_fuel_l: number
  alerts_by_severity: { info: number; warning: number; critical: number }
  hourly_activity?: { hour: string; avg_speed: number; avg_rpm: number }[]
}

const mainCardsStyle: React.CSSProperties = {
  background: '#ffffff',
  borderRadius: 12,
  padding: 20,
  boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
  border: '1px solid #e8ecf1',
  height: '100%',
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
      if (carsRes.data) setCars(carsRes.data?.cars || carsRes.data || [])
      if (alertsRes.data) setAlerts(alertsRes.data?.alerts || [])
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
          <Title level={2} style={{ margin: 0, fontWeight: 800 }}>
            <DashboardOutlined style={{ color: '#1890ff' }} /> Fleet Dashboard
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
          <Title level={2} style={{ margin: 0, fontWeight: 800 }}>
            <DashboardOutlined style={{ color: '#1890ff' }} /> Fleet Dashboard
          </Title>
          <Text type="secondary">Real-time overview of your fleet</Text>
        </div>
        <Card style={{ borderRadius: 12, border: '1px solid #e8ecf1' }}>
          <Empty
            description="No fleet data available. Add your first vehicle to get started."
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          />
        </Card>
      </div>
    )
  }

  const criticalWarning = (summary?.alerts_by_severity?.warning || 0) + (summary?.alerts_by_severity?.critical || 0)

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <Title level={2} style={{ margin: 0, fontWeight: 800 }}>
          <DashboardOutlined style={{ color: '#1890ff' }} /> Fleet Dashboard
        </Title>
        <Text type="secondary" style={{ fontSize: 15 }}>
          Real-time overview of your fleet
        </Text>
      </div>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <div style={mainCardsStyle}>
            <Space direction="vertical" size="small">
              <Space size={12}>
                <div style={{
                  width: 42,
                  height: 42,
                  borderRadius: 10,
                  background: 'linear-gradient(135deg, #1677ff, #69c0ff)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}>
                  <CarOutlined style={{ fontSize: 20, color: '#fff' }} />
                </div>
                <span style={{ color: '#64748b', fontSize: 13, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  Total Vehicles
                </span>
              </Space>
              <Text style={{ fontSize: 32, fontWeight: 800, color: '#1677ff', lineHeight: 1 }}>
                {summary?.total_cars || cars.length || 0}
              </Text>
            </Space>
          </div>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <div style={mainCardsStyle}>
            <Space direction="vertical" size="small">
              <Space size={12}>
                <div style={{
                  width: 42,
                  height: 42,
                  borderRadius: 10,
                  background: 'linear-gradient(135deg, #237804, #95de64)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}>
                  <CheckCircleOutlined style={{ fontSize: 20, color: '#fff' }} />
                </div>
                <span style={{ color: '#64748b', fontSize: 13, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  Active Now
                </span>
              </Space>
              <Text style={{ fontSize: 32, fontWeight: 800, color: '#389e0d', lineHeight: 1 }}>
                {summary?.active_cars || Object.keys(liveData).length}
              </Text>
            </Space>
          </div>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <div style={mainCardsStyle}>
            <Space direction="vertical" size="small">
              <Space size={12}>
                <div style={{
                  width: 42,
                  height: 42,
                  borderRadius: 10,
                  background: 'linear-gradient(135deg, #d46b08, #ffa940)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}>
                  <ArrowUpOutlined style={{ fontSize: 20, color: '#fff' }} />
                </div>
                <span style={{ color: '#64748b', fontSize: 13, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  Total Distance (km)
                </span>
              </Space>
              <Text style={{ fontSize: 32, fontWeight: 800, color: '#d46b08', lineHeight: 1 }}>
                {(summary?.total_distance_km || 0).toLocaleString()}
              </Text>
            </Space>
          </div>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <div style={mainCardsStyle}>
            <Space direction="vertical" size="small">
              <Space size={12}>
                <div style={{
                  width: 42,
                  height: 42,
                  borderRadius: 10,
                  background: criticalWarning > 0 ? 'linear-gradient(135deg, #cf1322, #ff7875)' : 'linear-gradient(135deg, #d4b106, #ffd666)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}>
                  <AlertOutlined style={{ fontSize: 20, color: '#fff' }} />
                </div>
                <span style={{ color: '#64748b', fontSize: 13, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  Active Alerts
                </span>
              </Space>
              <Text style={{ 
                fontSize: 32, 
                fontWeight: 800, 
                color: criticalWarning > 0 ? '#cf1322' : '#d4b106',
                lineHeight: 1,
              }}>
                {criticalWarning}
              </Text>
            </Space>
          </div>
        </Col>
      </Row>

      {/* Charts */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} lg={16}>
          <Card 
            title={
              <Space>
                <FireOutlined style={{ color: '#1890ff' }} />
                <span style={{ fontWeight: 700, fontSize: 15 }}>Fleet Activity (Last 24h)</span>
              </Space>
            } 
            style={{ borderRadius: 12, border: '1px solid #e8ecf1' }}
          >
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={chartData.length > 0 ? chartData : [
                { time: '00:00', speed: 0, rpm: 0 },
                { time: '06:00', speed: 0, rpm: 0 },
                { time: '12:00', speed: 0, rpm: 0 },
                { time: '18:00', speed: 0, rpm: 0 },
              ]}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e8ecf1" />
                <XAxis dataKey="time" stroke="#64748b" />
                <YAxis yAxisId="left" stroke="#64748b" />
                <YAxis yAxisId="right" orientation="right" stroke="#64748b" />
                <Tooltip 
                  contentStyle={{ 
                    borderRadius: 8,
                    border: '1px solid #e8ecf1',
                    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.07)',
                  }}
                />
                <Area
                  yAxisId="left"
                  type="monotone"
                  dataKey="speed"
                  stroke="#1890ff"
                  fill="#1890ff"
                  fillOpacity={0.15}
                  name="Speed (km/h)"
                />
                <Area
                  yAxisId="right"
                  type="monotone"
                  dataKey="rpm"
                  stroke="#52c41a"
                  fill="#52c41a"
                  fillOpacity={0.15}
                  name="RPM"
                />
              </AreaChart>
            </ResponsiveContainer>
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card 
            title={
              <Space>
                <WarningOutlined style={{ color: '#faad14' }} />
                <span style={{ fontWeight: 700, fontSize: 15 }}>Alert Severity</span>
              </Space>
            } 
            style={{ borderRadius: 12, border: '1px solid #e8ecf1' }}
          >
            <Space direction="vertical" size="large">
              <div>
                <Space style={{ marginBottom: 8 }}>
                  <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#ff4d4f' }} />
                  <Text>Critical</Text>
                </Space>
                <Progress 
                  percent={summary?.alerts_by_severity?.critical || 0} 
                  status="exception" 
                  strokeColor="#ff4d4f"
                  trailColor="#fff1f0"
                />
              </div>
              <div>
                <Space style={{ marginBottom: 8 }}>
                  <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#faad14' }} />
                  <Text>Warning</Text>
                </Space>
                <Progress 
                  percent={summary?.alerts_by_severity?.warning || 0} 
                  status="active"
                  strokeColor="#faad14"
                  trailColor="#fffbe6"
                />
              </div>
              <div>
                <Space style={{ marginBottom: 8 }}>
                  <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#1890ff' }} />
                  <Text>Info</Text>
                </Space>
                <Progress 
                  percent={summary?.alerts_by_severity?.info || 0} 
                  strokeColor="#1890ff"
                  trailColor="#e6f7ff"
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
            title={
              <Space size={8}>
                <CarOutlined style={{ color: '#1890ff' }} />
                <span style={{ fontWeight: 700, fontSize: 15 }}>Live Vehicles</span>
              </Space>
            }
            extra={<Tag color="success" style={{ borderRadius: 20, fontWeight: 600 }}>{Object.keys(liveData).length} Online</Tag>}
            style={{ borderRadius: 12, border: '1px solid #e8ecf1' }}
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
                    <Space size={12}>
                      <CarOutlined style={{ color: '#1890ff' }} />
                      <div>
                        <div style={{ fontWeight: 600 }}>{name}</div>
                        <Text type="secondary" style={{ fontSize: 12, color: '#64748b' }}>
                          {record.license_plate}
                        </Text>
                      </div>
                    </Space>
                  )
                },
                { 
                  title: 'Speed', 
                  dataIndex: 'id',
                  render: (id) => <Text strong>{liveData[id]?.speed?.toFixed(0) + ' km/h' || '-'}</Text>
                },
                { 
                  title: 'Status', 
                  dataIndex: 'status',
                  render: (status) => (
                    <Tag 
                      color={status === 'online' ? 'success' : 'default'}
                      style={{ borderRadius: 20, fontWeight: 600, fontSize: 12 }}
                    >
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
            title={
              <Space size={8}>
                <ClockCircleOutlined style={{ color: '#faad14' }} />
                <span style={{ fontWeight: 700, fontSize: 15 }}>Recent Alerts</span>
              </Space>
            }
            extra={<a href="/dashboard/alerts" style={{ fontWeight: 600, color: '#1890ff' }}>View All</a>}
            style={{ borderRadius: 12, border: '1px solid #e8ecf1' }}
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
                    <Tag 
                      color={
                        severity === 'critical' ? 'error' : 
                        severity === 'warning' ? 'warning' : 'processing'
                      }
                      style={{ borderRadius: 20, fontWeight: 600, fontSize: 12 }}
                    >
                      {severity}
                    </Tag>
                  )
                },
                { title: 'Message', dataIndex: 'message', ellipsis: true },
                { 
                  title: 'Time', 
                  dataIndex: 'created_at',
                  render: (time) => (
                    <Text type="secondary" style={{ color: '#64748b' }}>
                      <ClockCircleOutlined style={{ marginRight: 4 }} />
                      {new Date(time).toLocaleTimeString()}
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
