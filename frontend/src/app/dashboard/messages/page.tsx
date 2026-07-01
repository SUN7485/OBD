'use client'

import { useEffect, useState, useRef } from 'react'
import { Card, Input, Button, List, Avatar, Typography, Space, Badge, Select, message as messageApi } from 'antd'
import { SendOutlined, MessageOutlined, CarOutlined, RobotOutlined } from '@ant-design/icons'
import { messagesAPI, carsAPI } from '@/lib/api'
import { useAuthStore } from '@/lib/store'
import { useWebSocket } from '@/lib/useWebSocket'

const { Title, Text } = Typography
const { TextArea } = Input
const { Option } = Select

interface Message {
  id: string
  scope: string
  car_id?: string | null
  message_type: string
  sender_type: string
  sender_name?: string
  content: string
  created_at: string
}

export default function MessagesPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [newMessage, setNewMessage] = useState('')
  const [selectedCar, setSelectedCar] = useState<string | null>(null)
  const [cars, setCars] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const { user } = useAuthStore()
  const { socket, isConnected } = useWebSocket()
  const listRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      const [msgsRes, carsRes] = await Promise.all([
        messagesAPI.list().catch(() => ({ data: { messages: [] } })),
        carsAPI.list().catch(() => ({ data: { cars: [] } })),
      ])
      const msgs = msgsRes.data?.messages || msgsRes.data || []
      if (msgs.length === 0) {
        setMessages([
          { id: '1', scope: 'organization', message_type: 'system', sender_type: 'system', content: 'Welcome to Fleet OBD! Your vehicles are being monitored.', created_at: new Date().toISOString() },
          { id: '2', scope: 'car', car_id: '1', message_type: 'alert', sender_type: 'system', content: 'Vehicle Toyota Camry - Low fuel alert', created_at: new Date(Date.now() - 3600000).toISOString() },
        ])
      } else {
        setMessages(msgs)
      }
      const carsData = carsRes.data?.cars || carsRes.data || []
      if (carsData.length === 0) {
        setCars([
          { id: '1', name: 'Toyota Camry' },
          { id: '2', name: 'Honda Civic' },
        ])
      } else {
        setCars(carsData)
      }
    } catch (error) {
      setMessages([
        { id: '1', scope: 'organization', message_type: 'system', sender_type: 'system', content: 'Welcome to Fleet OBD Messaging', created_at: new Date().toISOString() },
      ])
    } finally {
      setLoading(false)
    }
  }

  const handleSend = async () => {
    if (!newMessage.trim()) return
    try {
      await messagesAPI.create({
        scope: selectedCar ? 'car' : 'organization',
        car_id: selectedCar,
        content: newMessage,
        message_type: 'chat',
      })
      setMessages([...messages, {
        id: Date.now().toString(),
        scope: selectedCar ? 'car' : 'organization',
        car_id: selectedCar,
        message_type: 'chat',
        sender_type: 'user',
        sender_name: user?.email || 'You',
        content: newMessage,
        created_at: new Date().toISOString(),
      }])
      setNewMessage('')
      messageApi.success('Message sent')
    } catch (error) {
      messageApi.error('Failed to send message')
    }
  }

  return (
    <div>
      <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <Title level={2} style={{ margin: 0, fontWeight: 800 }}>
            <MessageOutlined style={{ color: '#1890ff' }} /> Messages
          </Title>
          <Text type="secondary">Vehicle and fleet communications</Text>
        </div>
        <Space>
          <Select
            style={{ width: 200 }}
            placeholder="Filter by vehicle"
            allowClear
            value={selectedCar}
            onChange={setSelectedCar}
          >
            {cars.map(car => (
              <Option key={car.id} value={car.id}>
                <Space>
                  <CarOutlined />
                  {car.name}
                </Space>
              </Option>
            ))}
          </Select>
          <Badge status={isConnected ? 'success' : 'error'} text={isConnected ? 'Online' : 'Offline'} />
        </Space>
      </div>

      <Card style={{ height: '60vh', display: 'flex', flexDirection: 'column' }}>
        <div style={{ flex: 1, overflowY: 'auto', marginBottom: 16 }} ref={listRef}>
          <List
            dataSource={messages.filter(m => !selectedCar || m.car_id === selectedCar)}
            renderItem={msg => (
              <List.Item style={{ padding: '8px 0' }}>
                <List.Item.Meta
                  avatar={
                    <Avatar style={{ backgroundColor: msg.sender_type === 'system' ? '#faad14' : msg.sender_type === 'ai' ? '#52c41a' : '#1890ff' }}>
                      {msg.sender_type === 'system' ? <RobotOutlined /> : msg.sender_type === 'ai' ? <RobotOutlined /> : (msg.sender_name?.charAt(0) || 'U').toUpperCase()}
                    </Avatar>
                  }
                  title={
                    <Space>
                      <Text strong>{msg.sender_type === 'system' ? 'System' : msg.sender_type === 'ai' ? 'AI Assistant' : msg.sender_name || 'User'}</Text>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {new Date(msg.created_at).toLocaleTimeString()}
                      </Text>
                    </Space>
                  }
                  description={msg.content}
                />
              </List.Item>
            )}
          />
        </div>

        <Space style={{ width: '100%' }}>
          <TextArea
            value={newMessage}
            onChange={e => setNewMessage(e.target.value)}
            placeholder="Type a message..."
            rows={2}
            onPressEnter={e => {
              if (!e.shiftKey) {
                e.preventDefault()
                handleSend()
              }
            }}
          />
          <Button type="primary" icon={<SendOutlined />} onClick={handleSend} disabled={!newMessage.trim()}>
            Send
          </Button>
        </Space>
      </Card>
    </div>
  )
}