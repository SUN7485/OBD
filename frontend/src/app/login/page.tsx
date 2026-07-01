'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Form, Input, Button, Card, message, Tabs, Radio } from 'antd'
import { UserOutlined, LockOutlined, CarOutlined } from '@ant-design/icons'
import { useAuthStore } from '@/lib/store'
import { authAPI } from '@/lib/api'

export default function LoginPage() {
  const router = useRouter()
  const { setAuth } = useAuthStore()
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('login')

  const onLogin = async (values: { email: string; password: string }) => {
    setLoading(true)
    try {
      const response = await authAPI.login(values.email, values.password)
      const { access_token, refresh_token, user } = response.data
      setAuth(access_token, user)
      localStorage.setItem('token', access_token)
      localStorage.setItem('refresh_token', refresh_token)
      message.success('Welcome back!')
      router.push('/dashboard')
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Login failed')
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
      message.success('Account created! Please sign in.')
      setActiveTab('login')
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Registration failed')
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
              prefix={<UserOutlined style={{ color: 'var(--text-muted)' }} />} 
              placeholder="Email address" 
            />
          </Form.Item>
          <Form.Item name="password" rules={[{ required: true }]}>
            <Input.Password 
              prefix={<LockOutlined style={{ color: 'var(--text-muted)' }} />} 
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
            <Input prefix={<UserOutlined style={{ color: 'var(--text-muted)' }} />} placeholder="Full Name" />
          </Form.Item>
          <Form.Item 
            name="email" 
            rules={[{ required: true, type: 'email' }]}
          >
            <Input placeholder="Email" />
          </Form.Item>
          <Form.Item name="password" rules={[{ required: true, min: 6 }]}>
            <Input.Password prefix={<LockOutlined style={{ color: 'var(--text-muted)' }} />} placeholder="Password" />
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
      background: 'radial-gradient(1200px 600px at 50% -10%, #1E3A5F 0%, #0F172A 55%, #0B1220 100%)',
      padding: 24,
      position: 'relative',
      overflow: 'hidden',
    }}>
      {/* subtle decorative glow */}
      <div style={{
        position: 'absolute',
        top: '-15%',
        left: '50%',
        transform: 'translateX(-50%)',
        width: 520,
        height: 520,
        background: 'radial-gradient(circle, rgba(24,144,255,0.22) 0%, rgba(24,144,255,0) 70%)',
        pointerEvents: 'none',
      }} />

      <Card
        style={{
          width: '100%',
          maxWidth: 420,
          boxShadow: 'var(--shadow-xl)',
          borderRadius: 16,
          border: 'none',
          position: 'relative',
          zIndex: 1,
        }}
        styles={{ body: { padding: 32 } }}
      >
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <div style={{
            width: 64,
            height: 64,
            margin: '0 auto',
            borderRadius: 16,
            background: 'linear-gradient(135deg, #1890ff, #0958d9)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 8px 20px -6px rgba(24,144,255,0.55)',
          }}>
            <CarOutlined style={{ fontSize: 30, color: '#fff' }} />
          </div>
          <h1 style={{ fontSize: 26, fontWeight: 800, marginTop: 16, color: 'var(--text-primary)', letterSpacing: '-0.5px' }}>
            Fleet OBD
          </h1>
          <p style={{ color: 'var(--text-secondary)', marginTop: 4, fontSize: 14 }}>
            Real-time vehicle diagnostics &amp; monitoring
          </p>
        </div>

        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          centered
          size="large"
          items={tabItems}
        />

        {activeTab === 'login' && (
          <div style={{
            marginTop: 8,
            padding: '10px 12px',
            background: 'var(--surface-alt)',
            borderRadius: 8,
            border: '1px dashed var(--border)',
            textAlign: 'center',
            fontSize: 12.5,
            color: 'var(--text-secondary)',
          }}>
            <span style={{ fontWeight: 600 }}>Demo</span> · admin@test.com / admin123
          </div>
        )}
      </Card>
    </div>
  )
}