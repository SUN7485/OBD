'use client'

import { useEffect, useState } from 'react'
import { Card, Table, Tag, Progress, Typography, Avatar, Space } from 'antd'
import { TeamOutlined, TrophyOutlined, StarOutlined } from '@ant-design/icons'
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
      setDrivers(response.data || [])
    } catch (error) {
      console.error('Failed to load drivers:', error)
      // Use mock data for demo
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

  const getScoreColor = (score: number) => {
    if (score >= 90) return '#52c41a'
    if (score >= 70) return '#1890ff'
    if (score >= 50) return '#faad14'
    return '#ff4d4f'
  }

  const columns = [
    {
      title: 'Rank',
      key: 'rank',
      width: 60,
      render: (_: any, __: any, index: number) => {
        if (index === 0) return <TrophyOutlined style={{ color: '#faad14', fontSize: 20 }} />
        if (index === 1) return <TrophyOutlined style={{ color: '#d9d9d9', fontSize: 18 }} />
        if (index === 2) return <TrophyOutlined style={{ color: '#d48265', fontSize: 16 }} />
        return index + 1
      },
    },
    {
      title: 'Driver/Vehicle',
      dataIndex: 'car_name',
      render: (name: string) => (
        <Space>
          <Avatar style={{ backgroundColor: '#1890ff' }}>
            {name.charAt(0)}
          </Avatar>
          <Text strong>{name}</Text>
        </Space>
      ),
    },
    {
      title: 'Safety Score',
      dataIndex: 'safety_score',
      width: 150,
      render: (score: number) => (
        <Progress 
          percent={score} 
          strokeColor={getScoreColor(score)}
          size="small"
        />
      ),
    },
    {
      title: 'Efficiency',
      dataIndex: 'efficiency_score',
      width: 150,
      render: (score: number) => (
        <Progress 
          percent={score} 
          strokeColor={getScoreColor(score)}
          size="small"
        />
      ),
    },
    {
      title: 'Distance (km)',
      dataIndex: 'total_distance_km',
      render: (km: number) => km.toLocaleString(),
    },
    {
      title: 'Trips',
      dataIndex: 'total_trips',
    },
    {
      title: 'Incidents',
      key: 'incidents',
      render: (_: any, record: DriverScore) => (
        <Space>
          <Tag color={record.harsh_braking_count > 10 ? 'red' : 'default'}>
            Braking: {record.harsh_braking_count}
          </Tag>
          <Tag color={record.speeding_count > 5 ? 'red' : 'default'}>
            Speeding: {record.speeding_count}
          </Tag>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <Title level={2} style={{ margin: 0 }}>
          <TeamOutlined /> Driver Performance
        </Title>
        <Text type="secondary">Monitor driver behavior and safety scores</Text>
      </div>

      <Card>
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
