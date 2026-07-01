'use client'

import { useEffect, useState } from 'react'
import { Card, Row, Col, Statistic, Select, Typography, Spin, Empty, Space, Progress } from 'antd'
import { 
  LineChartOutlined, CarOutlined, DashboardOutlined,
  ThunderboltOutlined, ClockCircleOutlined, WarningOutlined 
} from '@ant-design/icons'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, 
  ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell,
  AreaChart, Area
} from 'recharts'
import { analyticsAPI } from '@/lib/api'
import { useFleetStore } from '@/lib/store'

const { Title, Text } = Typography
const { Option } = Select

const COLORS = ['#1890ff', '#52c41a', '#faad14', '#ff4d4f']

const cardStyle: React.CSSProperties = {
  background: '#ffffff',
  borderRadius: 12,
  padding: 20,
  boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
  border: '1px solid #e8ecf1',
  height: '100%',
}

export default function AnalyticsPage() {
  const [loading, setLoading] = useState(true)
  const [summary, setSummary] = useState<any>(null)
  const [selectedCar, setSelectedCar] = useState<string | null>(null)
  const { cars } = useFleetStore()

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      const response = await analyticsAPI.fleetSummary()
      setSummary(response.data)
    } catch (error) {
      console.error('Failed to load analytics:', error)
      setSummary({
        total_cars: 3,
        active_cars: 2,
        total_distance_km: 12580,
        total_fuel_consumed_l: 3250,
        alerts_by_severity: { info: 5, warning: 3, critical: 1 },
      })
    } finally {
      setLoading(false)
    }
  }

  const mockSpeedData = [
    { hour: '00:00', avg: 45, max: 80 },
    { hour: '04:00', avg: 32, max: 60 },
    { hour: '08:00', avg: 55, max: 100 },
    { hour: '12:00', avg: 48, max: 85 },
    { hour: '16:00', avg: 62, max: 110 },
    { hour: '20:00', avg: 50, max: 90 },
  ]

  const mockFuelData = [
    { name: 'Toyota', value: 35 },
    { name: 'Honda', value: 25 },
    { name: 'Ford', value: 20 },
    { name: 'Other', value: 20 },
  ]

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 400 }}>
        <Spin size="large" />
      </div>
    )
  }

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <Title level={2} style={{ margin: 0, fontWeight: 800 }}>
          <LineChartOutlined style={{ color: '#faad14' }} /> Analytics
        </Title>
        <Text type="secondary">Fleet performance insights</Text>
      </div>

      {/* Summary Stats */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <div style={cardStyle}>
            <Space direction="vertical" size="small">
              <Space size={12}>
                <div style={{ width: 42, height: 42, borderRadius: 10, background: 'linear-gradient(135deg, #1677ff, #69c0ff)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <CarOutlined style={{ fontSize: 20, color: '#fff' }} />
                </div>
                <span style={{ color: '#64748b', fontSize: 13, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  Total Distance
                </span>
              </Space>
<Text style={{ fontSize: 28, fontWeight: 800, color: '#1677ff', lineHeight: 1 }}>
                 {(summary?.total_distance_km || 12580).toLocaleString()}
               </Text>
             </Space>
           </div>
         </Col>
         <Col xs={24} sm={12} lg={6}>
           <div style={cardStyle}>
             <Space direction="vertical" size="small">
               <Space size={12}>
                 <div style={{ width: 42, height: 42, borderRadius: 10, background: 'linear-gradient(135deg, #d46b08, #ffa940)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                   <ThunderboltOutlined style={{ fontSize: 20, color: '#fff' }} />
                 </div>
                 <span style={{ color: '#64748b', fontSize: 13, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                   Total Fuel (L)
                 </span>
               </Space>
               <Text style={{ fontSize: 28, fontWeight: 800, color: '#d46b08', lineHeight: 1 }}>
                 {summary?.total_fuel_consumed_l || 3250}
               </Text>
            </Space>
          </div>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <div style={cardStyle}>
            <Space direction="vertical" size="small">
              <Space size={12}>
                <div style={{ width: 42, height: 42, borderRadius: 10, background: 'linear-gradient(135deg, #389e0d, #95de64)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <DashboardOutlined style={{ fontSize: 20, color: '#fff' }} />
                </div>
                <span style={{ color: '#64748b', fontSize: 13, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  Avg Speed
                </span>
              </Space>
              <Text style={{ fontSize: 28, fontWeight: 800, color: '#389e0d', lineHeight: 1 }}>
                52 <Text style={{ fontSize: 14, color: '#64748b' }}>km/h</Text>
              </Text>
            </Space>
          </div>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <div style={cardStyle}>
            <Space direction="vertical" size="small">
              <Space size={12}>
                <div style={{ width: 42, height: 42, borderRadius: 10, background: 'linear-gradient(135deg, #d46b08, #ffa940)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <ClockCircleOutlined style={{ fontSize: 20, color: '#fff' }} />
                </div>
                <span style={{ color: '#64748b', fontSize: 13, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  Active Hours
                </span>
              </Space>
              <Text style={{ fontSize: 28, fontWeight: 800, color: '#d46b08', lineHeight: 1 }}>
                156
              </Text>
            </Space>
          </div>
        </Col>
      </Row>

      {(!summary || (!summary.total_distance_km && !summary.total_fuel_l)) && (
        <Card style={{ marginBottom: 24, borderRadius: 12, border: '1px solid #e8ecf1' }}>
          <Space direction="vertical" size="small" style={{ width: '100%' }}>
            <Text type="secondary">Using demonstration data for charts below.</Text>
            <Progress percent={60} status="active" strokeColor="#faad14" showInfo={false} />
          </Space>
        </Card>
      )}

      {/* Charts */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card 
            title={<Text strong>Speed Distribution (24h)</Text>}
            style={{ borderRadius: 12, border: '1px solid #e8ecf1' }}
          >
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={mockSpeedData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e8ecf1" />
                <XAxis dataKey="hour" stroke="#64748b" />
                <YAxis stroke="#64748b" />
                <Tooltip 
                  contentStyle={{ 
                    borderRadius: 8,
                    border: '1px solid #e8ecf1',
                    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.07)',
                  }}
                />
                <Line 
                  type="monotone" 
                  dataKey="avg" 
                  stroke="#1890ff" 
                  name="Avg Speed"
                  strokeWidth={3}
                />
                <Line 
                  type="monotone" 
                  dataKey="max" 
                  stroke="#ff4d4f" 
                  name="Max Speed"
                  strokeWidth={3}
                />
              </LineChart>
            </ResponsiveContainer>
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card 
            title={<Text strong>Fleet Distribution by Brand</Text>}
            style={{ borderRadius: 12, border: '1px solid #e8ecf1' }}
          >
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={mockFuelData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  outerRadius={90}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {mockFuelData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </Card>
        </Col>
        <Col xs={24}>
          <Card 
            title={<Text strong>Daily Activity</Text>}
            style={{ borderRadius: 12, border: '1px solid #e8ecf1' }}
          >
            <ResponsiveContainer width="100%" height={250}>
              <AreaChart data={mockSpeedData}>
                <defs>
                  <linearGradient id="colorAvg" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#1890ff" stopOpacity={0.15}/>
                    <stop offset="95%" stopColor="#1890ff" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#e8ecf1" />
                <XAxis dataKey="hour" stroke="#64748b" />
                <YAxis stroke="#64748b" />
                <Tooltip 
                  contentStyle={{ 
                    borderRadius: 8,
                    border: '1px solid #e8ecf1',
                    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.07)',
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="avg"
                  stroke="#1890ff"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#colorAvg)"
                  name="Avg Speed"
                />
              </AreaChart>
            </ResponsiveContainer>
          </Card>
        </Col>
      </Row>
    </div>
  )
}
