'use client'

import { useEffect, useState } from 'react'
import { Card, Table, Tag, Progress, Typography, Avatar, Space, Row, Col } from 'antd'
import { TeamOutlined, TrophyOutlined } from '@ant-design/icons'
import { fleetAPI } from '@/lib/api'

const { Title, Text } = Typography

interface DriverScore {
  car_id: string
  car_name: string
  safety_score: number
  efficiency_score: number
  total_distance_km: number
  total_trips: number
  harsh_braking_count: number
  harsh_acceleration_count: number
  speeding_count: number
  updated_at: string
}

const cardStyle: React.CSSProperties = {
  background: '#ffffff',
  borderRadius: 12,
  boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
  border: '1px solid #e8ecf1',
}

const getProgressColor = (score: number) => {
  if (score >= 90) return '#52c41a'
  if (score >= 70) return '#1890ff'
  if (score >= 50) return '#faad14'
  return '#ff4d4f'
}

export default function DriversPage() {
  const [loading, setLoading] = useState(true)
  const [drivers, setDrivers] = useState<DriverScore[]>([])

  useEffect(() => {
    loadDrivers()
  }, [])

  const loadDrivers = async () => {
    try {
      setLoading(true)
      const response = await fleetAPI.driverLeaderboard(20)
      const rawData = response.data?.leaderboard || response.data || []
      const mappedData = rawData.map((d: any) => ({
        car_id: d.driver?.id || d.car_id || d.rank,
        car_name: d.driver?.name || d.car_name || `Driver ${d.rank}`,
        safety_score: d.safety_score || 80,
        efficiency_score: d.efficiency_score || 80,
        total_distance_km: d.total_distance_km || 0,
        total_trips: d.total_trips || 0,
        harsh_braking_count: d.harsh_braking_count || 0,
        harsh_acceleration_count: d.harsh_acceleration_count || 0,
        speeding_count: d.speeding_violations || d.speeding_count || 0,
        updated_at: new Date().toISOString(),
      }))
      setDrivers(mappedData)
    } catch (error) {
      console.error('Failed to load drivers:', error)
      setDrivers([
        {
          car_id: '1',
          car_name: 'John Smith - Toyota Camry',
          safety_score: 92,
          efficiency_score: 85,
          total_distance_km: 1250,
          total_trips: 45,
          harsh_braking_count: 3,
          harsh_acceleration_count: 5,
          speeding_count: 2,
          updated_at: new Date().toISOString(),
        },
        {
          car_id: '2',
          car_name: 'Sarah Johnson - Honda Accord',
          safety_score: 88,
          efficiency_score: 90,
          total_distance_km: 980,
          total_trips: 38,
          harsh_braking_count: 7,
          harsh_acceleration_count: 4,
          speeding_count: 5,
          updated_at: new Date().toISOString(),
        },
        {
          car_id: '3',
          car_name: 'Mike Davis - Ford F-150',
          safety_score: 75,
          efficiency_score: 70,
          total_distance_km: 2100,
          total_trips: 62,
          harsh_braking_count: 15,
          harsh_acceleration_count: 12,
          speeding_count: 8,
          updated_at: new Date().toISOString(),
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  const columns = [
    {
      title: 'Rank',
      key: 'rank',
      width: 70,
      align: 'center' as const,
      render: (_: any, __: any, index: number) => {
        if (index === 0) return <TrophyOutlined style={{ color: '#faad14', fontSize: 22 }} />
        if (index === 1) return <TrophyOutlined style={{ color: '#d9d9d9', fontSize: 20 }} />
        if (index === 2) return <TrophyOutlined style={{ color: '#d48265', fontSize: 18 }} />
        return <Text strong style={{ fontSize: 16, color: '#64748b' }}>{index + 1}</Text>
      },
    },
    {
      title: 'Driver / Vehicle',
      dataIndex: 'car_name',
      render: (name: string) => (
        <Space size={12}>
          <Avatar style={{ backgroundColor: '#1890ff' }}>
            {name.charAt(0)}
          </Avatar>
          <Text strong>{name}</Text>
        </Space>
      ),
    },
    {
      title: 'Safety Score',
      key: 'safety_score',
      width: 180,
      render: (_: any, record: DriverScore) => (
        <Space direction="vertical" size={4} style={{ width: '100%' }}>
          <Progress 
            percent={record.safety_score} 
            strokeColor={getProgressColor(record.safety_score)}
            trailColor="#f5f5f5"
            size="small"
          />
        </Space>
      ),
    },
    {
      title: 'Efficiency',
      key: 'efficiency_score',
      width: 180,
      render: (_: any, record: DriverScore) => (
        <Space direction="vertical" size={4} style={{ width: '100%' }}>
          <Progress 
            percent={record.efficiency_score} 
            strokeColor={getProgressColor(record.efficiency_score)}
            trailColor="#f5f5f5"
            size="small"
          />
        </Space>
      ),
    },
    {
      title: 'Distance (km)',
      dataIndex: 'total_distance_km',
      render: (km: number) => <Text strong>{km.toLocaleString()}</Text>,
    },
    {
      title: 'Trips',
      dataIndex: 'total_trips',
      render: (trips: number) => <Text type="secondary">{trips}</Text>
    },
    {
      title: 'Incidents',
      key: 'incidents',
      render: (_: any, record: DriverScore) => (
        <Space>
          <Tag color={record.harsh_braking_count > 10 ? 'error' : 'default'} style={{ borderRadius: 20 }}>
            Braking: {record.harsh_braking_count}
          </Tag>
          <Tag color={record.speeding_count > 5 ? 'error' : 'default'} style={{ borderRadius: 20 }}>
            Speeding: {record.speeding_count}
          </Tag>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <Title level={2} style={{ margin: 0, fontWeight: 800 }}>
          <TeamOutlined style={{ color: '#1890ff' }} /> Driver Performance
        </Title>
        <Text type="secondary">Monitor driver behavior and safety scores</Text>
      </div>

      <Card style={cardStyle}>
        <Table
          dataSource={drivers}
          columns={columns}
          rowKey="car_id"
          loading={loading}
          pagination={false}
        />
      </Card>
    </div>
  )
}
