'use client'

import { useEffect, useState, useRef } from 'react'
import { Card, Select, Space, Typography, Tag, Descriptions, Row, Col } from 'antd'
import { EnvironmentOutlined, CarOutlined } from '@ant-design/icons'
import { carsAPI } from '@/lib/api'
import { useFleetStore, useTelemetryStore } from '@/lib/store'

const { Title, Text } = Typography
const { Option } = Select

// Note: In production, use react-map-gl or leaflet
// This is a placeholder for the map visualization

interface Car {
  id: string
  name: string
  license_plate: string
  make: string
  model: string
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
        <Title level={2} style={{ margin: 0 }}>
          <EnvironmentOutlined /> Live Fleet Map
        </Title>
        <Text type="secondary">Real-time vehicle tracking</Text>
      </div>

      <Row gutter={16}>
        <Col xs={24} lg={18}>
          <Card style={{ height: '70vh' }}>
            {/* Map placeholder - In production integrate with Mapbox or Leaflet */}
            <div style={{
              width: '100%',
              height: '100%',
              minHeight: 500,
              background: '#f0f2f5',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: 8,
              flexDirection: 'column',
            }}>
              <EnvironmentOutlined style={{ fontSize: 64, color: '#1890ff' }} />
              <Title level={4} style={{ marginTop: 16 }}>Map View</Title>
              <Text type="secondary">
                Integrate with Mapbox or Leaflet for live tracking
              </Text>
              <Text type="secondary">
                Environment variable: NEXT_PUBLIC_MAPBOX_TOKEN
              </Text>
            </div>
          </Card>
        </Col>
        <Col xs={24} lg={6}>
          <Card title="Select Vehicle">
            <Select
              style={{ width: '100%' }}
              placeholder="Choose a vehicle"
              value={selectedCar}
              onChange={setSelectedCar}
              showSearch
              optionFilterProp="children"
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
            <Card title="Vehicle Details" style={{ marginTop: 16 }}>
              <Descriptions column={1} size="small">
                <Descriptions.Item label="Name">
                  {selectedData.car.name}
                </Descriptions.Item>
                <Descriptions.Item label="License">
                  {selectedData.car.license_plate}
                </Descriptions.Item>
                <Descriptions.Item label="Vehicle">
                  {selectedData.car.make} {selectedData.car.model}
                </Descriptions.Item>
              </Descriptions>
            </Card>
          )}

          {selectedData?.telemetry && (
            <Card title="Live Telemetry" style={{ marginTop: 16 }}>
              <Descriptions column={1} size="small">
                <Descriptions.Item label="Speed">
                  <Tag color="blue">
                    {selectedData.telemetry.speed?.toFixed(0)} km/h
                  </Tag>
                </Descriptions.Item>
                <Descriptions.Item label="RPM">
                  {selectedData.telemetry.rpm?.toFixed(0)}
                </Descriptions.Item>
                <Descriptions.Item label="Fuel Level">
                  <Tag color={selectedData.telemetry.fuel_level > 30 ? 'green' : 'red'}>
                    {selectedData.telemetry.fuel_level?.toFixed(1)}%
                  </Tag>
                </Descriptions.Item>
                <Descriptions.Item label="Coolant Temp">
                  {selectedData.telemetry.coolant_temp?.toFixed(1)}°C
                </Descriptions.Item>
                <Descriptions.Item label="Location">
                  {selectedData.telemetry.latitude?.toFixed(4)}, 
                  {selectedData.telemetry.longitude?.toFixed(4)}
                </Descriptions.Item>
              </Descriptions>
            </Card>
          )}
        </Col>
      </Row>
    </div>
  )
}
