'use client'

import React from 'react'
import { ConfigProvider, theme } from 'antd'

export default function AntdProvider({ children }: { children: React.ReactNode }) {
  return (
    <ConfigProvider
      theme={{
        algorithm: theme.compactAlgorithm,
        token: {
          colorPrimary: '#1890ff',
          colorPrimaryHover: '#1677cc',
          colorPrimaryActive: '#0958d9',
          borderRadius: 8,
          fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
          fontSize: 14,
          colorText: '#1a1a2e',
          colorTextSecondary: '#64748b',
          colorBgContainer: '#ffffff',
          colorBorder: '#e8ecf1',
          boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
        },
        components: {
          Card: {
            paddingLG: 20,
            borderRadiusLG: 12,
          },
          Button: {
            controlHeight: 40,
            paddingInline: 16,
            borderRadius: 8,
          },
          Input: {
            paddingInline: 12,
            borderRadius: 8,
          },
          Layout: {
            headerBg: '#0b1220',
            siderBg: '#0b1220',
          },
          Menu: {
            itemBg: 'transparent',
            itemSelectedBg: '#1890ff',
            itemSelectedColor: '#ffffff',
            itemHoverBg: 'rgba(255,255,255,0.08)',
          },
        },
      }}
    >
      {children}
    </ConfigProvider>
  )
}
