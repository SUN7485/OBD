'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Form, Input, Button, Card, message, Tabs, Radio, App } from 'antd'
import { UserOutlined, LockOutlined, CarOutlined } from '@ant-design/icons'
import { useAuthStore } from '@/lib/store'
import { authAPI } from '@/lib/api'

export default function LoginPage() {
  const router = useRouter()
  const { setAuth } = useAuthStore()
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('login')
  const { message: antdMessage } = App.useApp()

  const onLogin = async (values: { email: string; password: string }) => {
    setLoading(true)
    try {
      const response = await authAPI.login(values.email, values.password)
      const { access_token, user } = response.data
      setAuth(access_token, user)
      localStorage.setItem('token', access_token)
      antdMessage.success('Login successful!')
      router.push('/dashboard')
    } catch (error: any) {
      antdMessage.error(error.response?.data?.detail || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  const onRegister = async (values: { 
    email: string; 
    password: string; 
    organization_name: string;
    full_name?: string;
    role?: string;
  }) => {
    setLoading(true)
    try {
      await authAPI.register(
        values.email, 
        values.password, 
        values.organization_name,
        values.full_name || values.email.split('@')[0]
      )
      antdMessage.success('Registration successful! Please login.')
      setActiveTab('login')
    } catch (error: any) {
      antdMessage.error(error.response?.data?.detail || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  const tabItems = [
    {
      key: 'login',
      label: 'Sign In',
      children: (
        <Form onFinish={onLogin} layout="vertical" size="large">
          <Form.Item 
            name="email" 
            rules={[{ required: true, type: 'email' }]}
          >
            <Input 
              prefix={<UserOutlined />} 
              placeholder="Email address" 
            />
          </Form.Item>
          <Form.Item name="password" rules={[{ required: true }]}>
            <Input.Password 
              prefix={<LockOutlined />} 
              placeholder="Password" 
            />
          </Form.Item>
          <Form.Item>
            <Button 
              type="primary" 
              htmlType="submit" 
              loading={loading}
              block
            >
              Sign In
            </Button>
          </Form.Item>
        </Form>
      ),
    },
    {
      key: 'register',
      label: 'Register',
      children: (
        <Form onFinish={onRegister} layout="vertical" size="large">
          <Form.Item 
            name="organization_name" 
            rules={[{ required: true }]}
          >
            <Input placeholder="Company/Fleet Name" />
          </Form.Item>
          <Form.Item 
            name="full_name" 
            rules={[{ required: true }]}
          >
            <Input prefix={<UserOutlined />} placeholder="Full Name" />
          </Form.Item>
          <Form.Item 
            name="email" 
            rules={[{ required: true, type: 'email' }]}
          >
            <Input placeholder="Email" />
          </Form.Item>
          <Form.Item name="password" rules={[{ required: true, min: 6 }]}>
            <Input.Password prefix={<LockOutlined />} placeholder="Password" />
          </Form.Item>
          <Form.Item name="role" initialValue="driver">
            <Radio.Group>
              <Radio value="driver">Driver</Radio>
              <Radio value="fleet_manager">Fleet Manager</Radio>
            </Radio.Group>
          </Form.Item>
          <Form.Item>
            <Button 
              type="primary" 
              htmlType="submit" 
              loading={loading}
              block
            >
              Create Account
            </Button>
          </Form.Item>
        </Form>
      ),
    },
  ]

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'linear-gradient(135deg, #001529 0%, #1890ff 100%)',
    }}>
      <Card 
        style={{ 
          width: 420, 
          boxShadow: '0 8px 24px rgba(0,0,0,0.15)',
          borderRadius: 12
        }}
      >
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <CarOutlined style={{ fontSize: 48, color: '#1890ff' }} />
          <h1 style={{ fontSize: 24, fontWeight: 600, marginTop: 12 }}>
            Fleet OBD Platform
          </h1>
          <p style={{ color: '#8c8c8c' }}>
            Manage your fleet with real-time diagnostics
          </p>
        </div>

        <Tabs 
          activeKey={activeTab} 
          onChange={setActiveTab}
          centered
          items={tabItems}
        />
      </Card>
    </div>
  )
}