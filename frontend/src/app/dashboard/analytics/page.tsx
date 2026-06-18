'use client'

import { useEffect, useState } from 'react'
import { Card, Row, Col, Statistic, Select, Typography, Spin, Empty } from 'antd'
import { 
  LineChartOutlined, CarOutlined, DashboardOutlined,
  ThunderboltOutlined, ClockCircleOutlined 
} from '@ant-design/icons'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, 
  ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell
} from 'recharts'
import { analyticsAPI } from '@/lib/api'
import { useFleetStore } from '@/lib/store'

const { Title, Text } = Typography
const { Option } = Select

const COLORS = ['#1890ff', '#52c41a', '#faad14', '#ff4d4f']

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
      <div style={{ textAlign: 'center', padding: 100 }}>
        <Spin size="large" />
      </div>
    )
  }

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <Title level={2} style={{ margin: 0 }}>
          <LineChartOutlined /> Analytics
        </Title>
        <Text type="secondary">Fleet performance insights</Text>
      </div>

      {/* Summary Stats */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Total Distance (km)"
              value={summary?.total_distance_km || 12580}
              precision={1}
              prefix={<CarOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Total Fuel (L)"
              value={summary?.total_fuel_l || 3250}
              precision={1}
              prefix={<ThunderboltOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Avg Speed (km/h)"
              value={52}
              prefix={<DashboardOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Active Hours"
              value={156}
              prefix={<ClockCircleOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* Charts */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card title="Speed Distribution (24h)">
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={mockSpeedData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="hour" />
                <YAxis />
                <Tooltip />
                <Line 
                  type="monotone" 
                  dataKey="avg" 
                  stroke="#1890ff" 
                  name="Avg Speed"
                  strokeWidth={2}
                />
                <Line 
                  type="monotone" 
                  dataKey="max" 
                  stroke="#ff4d4f" 
                  name="Max Speed"
                  strokeWidth={2}
                />
              </LineChart>
            </ResponsiveContainer>
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="Fleet Distribution by Brand">
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={mockFuelData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
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
          <Card title="Daily Activity">
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={mockSpeedData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="hour" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="avg" fill="#1890ff" name="Avg Speed" />
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </Col>
      </Row>
    </div>
  )
}
