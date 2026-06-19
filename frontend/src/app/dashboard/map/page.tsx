'use client'

import { useEffect, useState, useRef } from 'react'
import { Card, Select, Space, Typography, Tag, Descriptions, Row, Col } from 'antd'
import { EnvironmentOutlined, CarOutlined, ClockCircleOutlined } from '@ant-design/icons'
import { carsAPI } from '@/lib/api'
import { useFleetStore, useTelemetryStore } from '@/lib/store'

const { Title, Text } = Typography
const { Option } = Select
const { Item } = Descriptions

interface Car {
  id: string
  name: string
  license_plate: string
  make: string
  model: string
}

const cardStyle: React.CSSProperties = {
  background: '#ffffff',
  borderRadius: 12,
  boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
  border: '1px solid #e8ecf1',
}

export default function MapPage() {
  const [loading, setLoading] = useState(false)
  const [selectedCar, setSelectedCar] = useState<string | null>(null)
  const { cars, setCars } = useFleetStore()
  const { liveData } = useTelemetryStore()
  const mapRef = useRef<any>(null)

  useEffect(() => {
    loadCars()
  }, [])

  const loadCars = async () => {
    try {
      setLoading(true)
      const response = await carsAPI.list()
      setCars(response.data || [])
    } catch (error) {
      console.error('Failed to load cars:', error)
    } finally {
      setLoading(false)
    }
  }

  const getSelectedCarData = () => {
    if (!selectedCar) return null
    const car = cars.find(c => c.id === selectedCar)
    const telemetry = liveData[selectedCar]
    return { car, telemetry }
  }

  const selectedData = getSelectedCarData()

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <Title level={2} style={{ margin: 0, fontWeight: 800 }}>
          <EnvironmentOutlined style={{ color: '#52c41a' }} /> Live Fleet Map
        </Title>
        <Text type="secondary">Real-time vehicle tracking</Text>
      </div>

      <Row gutter={[16, 16]}>
        <Col xs={24}>
          <Card 
            style={{ height: '50vh', minHeight: 320 }}
            styles={{ body: { height: '100%' } }}
          >
            <div style={{
              width: '100%',
              height: '100%',
              background: '#f5f6fa',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: 8,
              flexDirection: 'column',
            }}>
              <EnvironmentOutlined style={{ fontSize: 48, color: '#1890ff' }} />
              <Title level={4} style={{ marginTop: 12, fontWeight: 700 }}>Map View</Title>
              <Text type="secondary">
                Integrate with Mapbox or Leaflet for live tracking
              </Text>
              <Text type="secondary" style={{ marginTop: 4 }}>
                Environment variable: NEXT_PUBLIC_MAPBOX_TOKEN
              </Text>
            </div>
          </Card>
        </Col>
        <Col xs={24} lg={8} style={{ maxWidth: 360, alignSelf: 'flex-start' }}>
          <Card 
            title={<Text strong>Select Vehicle</Text>}
            style={{ borderRadius: 12, border: '1px solid #e8ecf1' }}
          >
            <Select
              style={{ width: '100%' }}
              placeholder="Choose a vehicle"
              value={selectedCar}
              onChange={setSelectedCar}
              showSearch
              optionFilterProp="children"
              size="large"
            >
              {cars.map(car => (
                <Option key={car.id} value={car.id}>
                  <Space>
                    <CarOutlined />
                    {car.name} ({car.license_plate})
                  </Space>
                </Option>
              ))}
            </Select>
          </Card>

          {selectedData && selectedData.car && (
            <Card 
              title={<Text strong>Vehicle Details</Text>}
              style={{ marginTop: 16, borderRadius: 12, border: '1px solid #e8ecf1' }}
            >
              <Descriptions column={1} size="small">
                <Item label="Name">{selectedData.car.name}</Item>
                <Item label="License">{selectedData.car.license_plate}</Item>
                <Item label="Vehicle">{selectedData.car.make} {selectedData.car.model}</Item>
              </Descriptions>
            </Card>
          )}

          {selectedData?.telemetry && (
            <Card 
              title={<Text strong>Live Telemetry</Text>}
              style={{ marginTop: 16, borderRadius: 12, border: '1px solid #e8ecf1' }}
            >
              <Descriptions column={1} size="small">
                <Item label="Speed">
                  <Tag color="success" style={{ borderRadius: 20 }}>
                    {selectedData.telemetry.speed?.toFixed(0)} km/h
                  </Tag>
                </Item>
                <Item label="RPM">
                  <Text strong>{selectedData.telemetry.rpm?.toFixed(0)}</Text>
                </Item>
                <Item label="Fuel Level">
                  <Tag color={selectedData.telemetry.fuel_level > 30 ? 'success' : 'error'} style={{ borderRadius: 20 }}>
                    {selectedData.telemetry.fuel_level?.toFixed(1)}%
                  </Tag>
                </Item>
                <Item label="Coolant Temp">
                  <Text>{selectedData.telemetry.coolant_temp?.toFixed(1)}°C</Text>
                </Item>
                <Item label="Location">
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    <ClockCircleOutlined style={{ marginRight: 4 }} />
                    {selectedData.telemetry.latitude?.toFixed(4)}, {selectedData.telemetry.longitude?.toFixed(4)}
                  </Text>
                </Item>
              </Descriptions>
            </Card>
          )}
        </Col>
      </Row>
    </div>
  )
}
