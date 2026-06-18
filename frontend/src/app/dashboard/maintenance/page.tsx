'use client'

import { useEffect, useState } from 'react'
import { 
  Card, Table, Tag, Button, Space, Modal, Form, DatePicker, 
  Select, InputNumber, Typography, Row, Col, Statistic, message,
  Progress, Descriptions 
} from 'antd'
import { 
  ToolOutlined, PlusOutlined, CalendarOutlined, 
  WarningOutlined, CheckCircleOutlined 
} from '@ant-design/icons'
import { fleetAPI, carsAPI } from '@/lib/api'
import dayjs from 'dayjs'

const { Title, Text } = Typography
const { Option } = Select

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
      case 'completed': return 'green'
      case 'in_progress': return 'blue'
      case 'overdue': return 'red'
      default: return 'default'
    }
  }

  const columns = [
    { title: 'Vehicle', dataIndex: 'car_name' },
    { title: 'Type', dataIndex: 'maintenance_type', render: (type: string) => <Tag>{type}</Tag> },
    { title: 'Scheduled', dataIndex: 'scheduled_date', render: (date: string) => dayjs(date).format('MMM DD, YYYY') },
    { title: 'Status', dataIndex: 'status', render: (status: string) => <Tag color={getStatusColor(status)}>{status}</Tag> },
    { title: 'Est. Cost', dataIndex: 'estimated_cost', render: (cost: number) => cost ? `$${cost}` : '-' },
  ]

  const stats = {
    scheduled: maintenance.filter(m => m.status === 'scheduled').length,
    overdue: maintenance.filter(m => m.status === 'overdue').length,
    completed: maintenance.filter(m => m.status === 'completed').length,
  }

  return (
    <div>
      <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between' }}>
        <div>
          <Title level={2} style={{ margin: 0 }}><ToolOutlined /> Maintenance</Title>
          <Text type="secondary">Schedule and track vehicle maintenance</Text>
        </div>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
          Schedule
        </Button>
      </div>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={8}><Card><Statistic title="Scheduled" value={stats.scheduled} prefix={<CalendarOutlined />} /></Card></Col>
        <Col span={8}><Card><Statistic title="Overdue" value={stats.overdue} prefix={<WarningOutlined />} valueStyle={{ color: '#ff4d4f' }} /></Card></Col>
        <Col span={8}><Card><Statistic title="Completed" value={stats.completed} prefix={<CheckCircleOutlined />} valueStyle={{ color: '#52c41a' }} /></Card></Col>
      </Row>

      <Card>
        <Table dataSource={maintenance} columns={columns} rowKey="id" loading={loading} />
      </Card>

      <Modal title="Schedule Maintenance" open={modalOpen} onCancel={() => setModalOpen(false)} onOk={form.submit}>
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item name="car_id" label="Vehicle" rules={[{ required: true }]}>
            <Select>{cars.map(car => <Option key={car.id} value={car.id}>{car.name}</Option>)}</Select>
          </Form.Item>
          <Form.Item name="maintenance_type" label="Type" rules={[{ required: true }]}>
            <Select><Option value="oil_change">Oil Change</Option><Option value="tire_rotation">Tire Rotation</Option><Option value="brake_service">Brake Service</Option></Select>
          </Form.Item>
          <Form.Item name="scheduled_date" label="Date" rules={[{ required: true }]}><DatePicker style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="estimated_cost" label="Cost"><InputNumber style={{ width: '100%' }} min={0} /></Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
