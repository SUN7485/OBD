'use client'

import { useEffect, useState } from 'react'
import { 
  Card, Table, Tag, Button, Space, Modal, Form, Input, Select, 
  Row, Col, Statistic, Typography, Popconfirm, message 
} from 'antd'
import { 
  PlusOutlined, EditOutlined, DeleteOutlined, 
  CarOutlined, SearchOutlined, ReloadOutlined 
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
      setCars(response.data || [])
    } catch (error) {
      message.error('Failed to load cars')
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
        <Space>
          <CarOutlined style={{ fontSize: 24, color: '#1890ff' }} />
          <div>
            <div style={{ fontWeight: 500 }}>{name}</div>
            <Text type="secondary" style={{ fontSize: 12 }}>
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
          <Tag color={isOnline ? 'green' : 'default'}>
            {isOnline ? 'Online' : 'Offline'}
          </Tag>
        )
      }
    },
    { 
      title: 'Live Speed', 
      dataIndex: 'id',
      render: (id: string) => liveData[id]?.speed?.toFixed(0) + ' km/h' || '-'
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
      <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between' }}>
        <div>
          <Title level={2} style={{ margin: 0 }}>Fleet Management</Title>
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

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic 
              title="Total Vehicles" 
              value={cars.length} 
              prefix={<CarOutlined />} 
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic 
              title="Online" 
              value={Object.keys(liveData).length} 
              valueStyle={{ color: '#52c41a' }}
              prefix={<CarOutlined />} 
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic 
              title="Offline" 
              value={cars.length - Object.keys(liveData).length} 
              valueStyle={{ color: '#8c8c8c' }}
              prefix={<CarOutlined />} 
            />
          </Card>
        </Col>
      </Row>

      <Card>
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
