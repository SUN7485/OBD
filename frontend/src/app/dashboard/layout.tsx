'use client'

import { useEffect } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import Link from 'next/link'
import { Layout, Menu, Avatar, Dropdown, Badge, Space } from 'antd'
import {
  DashboardOutlined,
  CarOutlined,
  AlertOutlined,
  MessageOutlined,
  LineChartOutlined,
  EnvironmentOutlined,
  TeamOutlined,
  ToolOutlined,
  SettingOutlined,
  LogoutOutlined,
  BellOutlined,
} from '@ant-design/icons'
import { useAuthStore, useAlertStore } from '@/lib/store'
import { useWebSocket } from '@/lib/useWebSocket'

const { Header, Sider, Content } = Layout

const menuItems = [
  { key: '/dashboard', icon: <DashboardOutlined />, label: 'Overview' },
  { key: '/dashboard/fleet', icon: <CarOutlined />, label: 'Fleet' },
  { key: '/dashboard/map', icon: <EnvironmentOutlined />, label: 'Map' },
  { key: '/dashboard/alerts', icon: <AlertOutlined />, label: 'Alerts' },
  { key: '/dashboard/analytics', icon: <LineChartOutlined />, label: 'Analytics' },
  { key: '/dashboard/drivers', icon: <TeamOutlined />, label: 'Drivers' },
  { key: '/dashboard/maintenance', icon: <ToolOutlined />, label: 'Maintenance' },
  { key: '/dashboard/messages', icon: <MessageOutlined />, label: 'Messages' },
]

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const router = useRouter()
  const pathname = usePathname()
  const { user, logout } = useAuthStore()
  const { unreadCount } = useAlertStore()

  // Connect WebSocket
  useWebSocket()

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) {
      router.push('/login')
    }
  }, [router])

  const handleLogout = () => {
    logout()
    localStorage.removeItem('token')
    router.push('/login')
  }

  const userMenu = {
    items: [
      {
        key: 'profile',
        icon: <SettingOutlined />,
        label: 'Settings',
      },
      {
        type: 'divider' as const,
      },
      {
        key: 'logout',
        icon: <LogoutOutlined />,
        label: 'Logout',
        onClick: handleLogout,
      },
    ],
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider width={240} theme="dark" breakpoint="lg" collapsedWidth="0">
        <div style={{
          height: 64,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          borderBottom: '1px solid rgba(255,255,255,0.1)',
        }}>
          <CarOutlined style={{ fontSize: 28, color: '#1890ff', marginRight: 8 }} />
          <span style={{ color: '#fff', fontSize: 18, fontWeight: 600 }}>
            Fleet OBD
          </span>
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[pathname]}
          items={menuItems.map(item => ({
            ...item,
            label: <Link href={item.key}>{item.label}</Link>,
          }))}
        />
      </Sider>
      <Layout>
        <Header style={{
          background: '#fff',
          padding: '0 24px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          boxShadow: '0 1px 4px rgba(0,0,0,0.1)',
        }}>
          <div></div>
          <Space size="large">
            <Badge count={unreadCount} size="small">
              <BellOutlined style={{ fontSize: 20, cursor: 'pointer' }} />
            </Badge>
            <Dropdown menu={userMenu} placement="bottomRight">
              <Space style={{ cursor: 'pointer' }}>
                <Avatar style={{ backgroundColor: '#1890ff' }}>
                  {user?.email?.charAt(0).toUpperCase()}
                </Avatar>
                <span>{user?.email}</span>
              </Space>
            </Dropdown>
          </Space>
        </Header>
        <Content style={{ margin: 24, padding: 24, background: '#fff', borderRadius: 8 }}>
          {children}
        </Content>
      </Layout>
    </Layout>
  )
}
