'use client'

import { useEffect, useState } from 'react'
import { 
  Card, Table, Tag, Button, Space, Modal, Form, Input, Select, 
  Row, Col, Statistic, Typography, Popconfirm, message 
} from 'antd'
import { 
  PlusOutlined, EditOutlined, DeleteOutlined, 
  CarOutlined
} from '@ant-design/icons'
import { carsAPI, fleetAPI } from '@/lib/api'
import { useFleetStore, useTelemetryStore } from '@/lib/store'

const { Title, Text } = Typography
const { Option } = Select

interface Car {
  id: string
  name: string
  license_plate: string
  make: string
  model: string
  year: number
  status: string
  vin?: string
  assigned_driver?: string
}

const mainCardsStyle: React.CSSProperties = {
  background: '#ffffff',
  borderRadius: 12,
  padding: 20,
  boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
  border: '1px solid #e8ecf1',
  height: '100%',
}

export default function FleetPage() {
  const [loading, setLoading] = useState(true)
  const [cars, setCars] = useState<Car[]>([])
  const [modalOpen, setModalOpen] = useState(false)
  const [editingCar, setEditingCar] = useState<Car | null>(null)
  const [form] = Form.useForm()
  const { selectCar } = useFleetStore()
  const { liveData } = useTelemetryStore()

  useEffect(() => {
    loadCars()
  }, [])

  const loadCars = async () => {
    try {
      setLoading(true)
      const response = await carsAPI.list()
      const carsData = response.data?.cars || response.data || []
      if (carsData.length === 0) {
        setCars([
          { id: '1', name: 'Toyota Camry', license_plate: 'ABC-1234', make: 'Toyota', model: 'Camry', year: 2022, status: 'online' },
          { id: '2', name: 'Honda Civic', license_plate: 'XYZ-5678', make: 'Honda', model: 'Civic', year: 2021, status: 'online' },
          { id: '3', name: 'Ford F-150', license_plate: 'DEF-9012', make: 'Ford', model: 'F-150', year: 2023, status: 'offline' },
        ])
      } else {
        setCars(carsData)
      }
    } catch (error) {
      setCars([
        { id: '1', name: 'Toyota Camry', license_plate: 'ABC-1234', make: 'Toyota', model: 'Camry', year: 2022, status: 'online' },
        { id: '2', name: 'Honda Civic', license_plate: 'XYZ-5678', make: 'Honda', model: 'Civic', year: 2021, status: 'online' },
        { id: '3', name: 'Ford F-150', license_plate: 'DEF-9012', make: 'Ford', model: 'F-150', year: 2023, status: 'offline' },
      ])
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (values: any) => {
    try {
      if (editingCar) {
        await carsAPI.update(editingCar.id, values)
        message.success('Car updated successfully')
      } else {
        await carsAPI.create(values)
        message.success('Car created successfully')
      }
      setModalOpen(false)
      form.resetFields()
      setEditingCar(null)
      loadCars()
    } catch (error) {
      message.error('Operation failed')
    }
  }

  const handleDelete = async (id: string) => {
    try {
      await carsAPI.delete(id)
      message.success('Car deleted')
      loadCars()
    } catch (error) {
      message.error('Delete failed')
    }
  }

  const columns = [
    {
      title: 'Vehicle',
      dataIndex: 'name',
      render: (name: string, record: Car) => (
        <Space size={12}>
          <CarOutlined style={{ fontSize: 20, color: '#1890ff' }} />
          <div>
            <div style={{ fontWeight: 600 }}>{name}</div>
            <Text type="secondary" style={{ fontSize: 12, color: '#64748b' }}>
              {record.make} {record.model} ({record.year})
            </Text>
          </div>
        </Space>
      ),
    },
    { title: 'License Plate', dataIndex: 'license_plate' },
    { title: 'VIN', dataIndex: 'vin' },
    { 
      title: 'Status', 
      dataIndex: 'status',
      render: (status: string) => {
        const isOnline = liveData[status as any] !== undefined
        return (
          <Tag color={isOnline ? 'success' : 'default'} style={{ borderRadius: 20 }}>
            {isOnline ? 'Online' : 'Offline'}
          </Tag>
        )
      }
    },
    { 
      title: 'Live Speed', 
      dataIndex: 'id',
      render: (id: string) => <Text strong>{liveData[id]?.speed?.toFixed(0) + ' km/h' || '-'}</Text>
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: any, record: Car) => (
        <Space>
          <Button 
            type="link" 
            icon={<EditOutlined />} 
            onClick={() => {
              setEditingCar(record)
              form.setFieldsValue(record)
              setModalOpen(true)
            }}
          />
          <Popconfirm
            title="Delete this car?"
            onConfirm={() => handleDelete(record.id)}
          >
            <Button type="link" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <Title level={2} style={{ margin: 0, fontWeight: 800 }}>
            <CarOutlined style={{ color: '#1890ff' }} /> Fleet Management
          </Title>
          <Text type="secondary">Manage your vehicles</Text>
        </div>
        <Button 
          type="primary" 
          icon={<PlusOutlined />}
          onClick={() => {
            setEditingCar(null)
            form.resetFields()
            setModalOpen(true)
          }}
        >
          Add Vehicle
        </Button>
      </div>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={8}>
          <div style={mainCardsStyle}>
            <Space direction="vertical" size="small">
              <span style={{ color: '#64748b', fontSize: 13, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                Total Vehicles
              </span>
              <Text style={{ fontSize: 32, fontWeight: 800, color: '#1677ff', lineHeight: 1 }}>
                {cars.length}
              </Text>
            </Space>
          </div>
        </Col>
        <Col xs={24} sm={8}>
          <div style={mainCardsStyle}>
            <Space direction="vertical" size="small">
              <span style={{ color: '#64748b', fontSize: 13, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                Online
              </span>
              <Text style={{ fontSize: 32, fontWeight: 800, color: '#389e0d', lineHeight: 1 }}>
                {Object.keys(liveData).length}
              </Text>
            </Space>
          </div>
        </Col>
        <Col xs={24} sm={8}>
          <div style={mainCardsStyle}>
            <Space direction="vertical" size="small">
              <span style={{ color: '#64748b', fontSize: 13, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                Offline
              </span>
              <Text style={{ fontSize: 32, fontWeight: 800, color: '#8c8c8c', lineHeight: 1 }}>
                {cars.length - Object.keys(liveData).length}
              </Text>
            </Space>
          </div>
        </Col>
      </Row>

      <Card style={{ borderRadius: 12, border: '1px solid #e8ecf1' }}>
        <Table
          dataSource={cars}
          columns={columns}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10 }}
        />
      </Card>

      <Modal
        title={editingCar ? 'Edit Vehicle' : 'Add Vehicle'}
        open={modalOpen}
        onCancel={() => {
          setModalOpen(false)
          setEditingCar(null)
          form.resetFields()
        }}
        onOk={form.submit}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item name="name" label="Name" rules={[{ required: true }]}>
            <Input placeholder="e.g., Company Car 1" />
          </Form.Item>
          <Form.Item name="license_plate" label="License Plate" rules={[{ required: true }]}>
            <Input placeholder="e.g., ABC-1234" />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="make" label="Make" rules={[{ required: true }]}>
                <Input placeholder="e.g., Toyota" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="model" label="Model" rules={[{ required: true }]}>
                <Input placeholder="e.g., Camry" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="year" label="Year">
                <Input type="number" placeholder="e.g., 2023" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="vin" label="VIN">
                <Input placeholder="17-character VIN" />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>
    </div>
  )
}
