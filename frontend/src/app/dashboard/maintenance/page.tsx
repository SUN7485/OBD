'use client'

import { useEffect, useState } from 'react'
import { 
  Card, Table, Tag, Button, Space, Modal, Form, DatePicker, 
  Select, InputNumber, Typography, Row, Col, Statistic, message
} from 'antd'
import { 
  ToolOutlined, PlusOutlined, CalendarOutlined, 
  WarningOutlined, CheckCircleOutlined 
} from '@ant-design/icons'
import { fleetAPI, carsAPI } from '@/lib/api'
import dayjs from 'dayjs'

const { Title, Text } = Typography
const { Option } = Select

const cardStyle: React.CSSProperties = {
  background: '#ffffff',
  borderRadius: 12,
  padding: 16,
  boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
  border: '1px solid #e8ecf1',
}

interface Maintenance {
  id: string
  car_id: string
  car_name: string
  maintenance_type: string
  scheduled_date: string
  status: 'scheduled' | 'in_progress' | 'completed' | 'overdue'
  estimated_cost?: number
  notes?: string
}

export default function MaintenancePage() {
  const [loading, setLoading] = useState(true)
  const [maintenance, setMaintenance] = useState<Maintenance[]>([])
  const [cars, setCars] = useState<any[]>([])
  const [modalOpen, setModalOpen] = useState(false)
  const [selectedCar, setSelectedCar] = useState<string | null>(null)
  const [form] = Form.useForm()

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      const [maintRes, carsRes] = await Promise.all([
        fleetAPI.listMaintenance().catch(() => ({ data: [] })),
        carsAPI.list().catch(() => ({ data: [] })),
      ])
      setMaintenance(maintRes.data || [])
      setCars(carsRes.data || [])
    } catch (error) {
      console.error('Failed to load maintenance:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (values: any) => {
    try {
      await fleetAPI.createMaintenance({
        ...values,
        scheduled_date: values.scheduled_date.format('YYYY-MM-DD'),
      })
      message.success('Maintenance scheduled')
      setModalOpen(false)
      form.resetFields()
      loadData()
    } catch (error) {
      message.error('Failed to schedule maintenance')
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'success'
      case 'in_progress': return 'processing'
      case 'overdue': return 'error'
      default: return 'default'
    }
  }

  const columns = [
    { 
      title: 'Vehicle', 
      dataIndex: 'car_name',
      render: (text: string) => <Text strong>{text}</Text>
    },
    { 
      title: 'Type', 
      dataIndex: 'maintenance_type',
      render: (type: string) => <Tag style={{ borderRadius: 6 }}>{type}</Tag>
    },
    { 
      title: 'Scheduled', 
      dataIndex: 'scheduled_date', 
      render: (date: string) => dayjs(date).format('MMM DD, YYYY'),
    },
    { 
      title: 'Status', 
      dataIndex: 'status', 
      render: (status: string) => <Tag color={getStatusColor(status)} style={{ borderRadius: 20, fontWeight: 500 }}>{status}</Tag>
    },
    { 
      title: 'Est. Cost', 
      dataIndex: 'estimated_cost', 
      render: (cost: number) => cost ? <Text strong>${cost}</Text> : <Text type="secondary">-</Text> 
    },
  ]

  const stats = {
    scheduled: maintenance.filter(m => m.status === 'scheduled').length,
    overdue: maintenance.filter(m => m.status === 'overdue').length,
    completed: maintenance.filter(m => m.status === 'completed').length,
  }

  return (
    <div>
      <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <Title level={2} style={{ margin: 0, fontWeight: 800 }}>
            <ToolOutlined style={{ color: '#faad14' }} /> Maintenance
          </Title>
          <Text type="secondary">Schedule and track vehicle maintenance</Text>
        </div>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
          Schedule
        </Button>
      </div>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24}>
          <Space size={16}>
            <div style={cardStyle}>
              <Statistic 
                title={<Text style={{ fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.5px', color: '#64748b' }}>Scheduled</Text>}
                value={stats.scheduled} 
                prefix={<CalendarOutlined style={{ color: '#1890ff' }} />}
              />
            </div>
            <div style={cardStyle}>
              <Statistic 
                title={<Text style={{ fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.5px', color: '#64748b' }}>Overdue</Text>}
                value={stats.overdue} 
                valueStyle={{ color: '#ff4d4f' }}
                prefix={<WarningOutlined />}
              />
            </div>
            <div style={cardStyle}>
              <Statistic 
                title={<Text style={{ fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.5px', color: '#64748b' }}>Completed</Text>}
                value={stats.completed} 
                valueStyle={{ color: '#52c41a' }}
                prefix={<CheckCircleOutlined />}
              />
            </div>
          </Space>
        </Col>
      </Row>

      <Card style={{ borderRadius: 12, border: '1px solid #e8ecf1' }}>
        <Table dataSource={maintenance} columns={columns} rowKey="id" loading={loading} />
      </Card>

      <Modal title="Schedule Maintenance" open={modalOpen} onCancel={() => setModalOpen(false)} onOk={form.submit}>
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item name="car_id" label="Vehicle" rules={[{ required: true }]}>
            <Select>{cars.map(car => <Option key={car.id} value={car.id}>{car.name}</Option>)}</Select>
          </Form.Item>
          <Form.Item name="maintenance_type" label="Type" rules={[{ required: true }]}>
            <Select>
              <Option value="oil_change">Oil Change</Option>
              <Option value="tire_rotation">Tire Rotation</Option>
              <Option value="brake_service">Brake Service</Option>
            </Select>
          </Form.Item>
          <Form.Item name="scheduled_date" label="Date" rules={[{ required: true }]}>
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="estimated_cost" label="Cost">
            <InputNumber style={{ width: '100%' }} min={0} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
