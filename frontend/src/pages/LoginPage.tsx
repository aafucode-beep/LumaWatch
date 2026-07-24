import { useState } from 'react'
import { Button, Card, Form, Input, Typography, message } from 'antd'
import { LockOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { api, tokenStore } from '../api/client'

export default function LoginPage() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)

  const onFinish = async (values: { password: string }) => {
    setLoading(true)
    try {
      const token = await api.login(values.password)
      tokenStore.set(token)
      message.success('登录成功')
      navigate('/', { replace: true })
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '登录失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg,#1677ff22,#722ed122)',
      }}
    >
      <Card style={{ width: 360 }}>
        <Typography.Title level={4} style={{ textAlign: 'center' }}>
          建筑照明网站情报库
        </Typography.Title>
        <Typography.Paragraph type="secondary" style={{ textAlign: 'center' }}>
          请输入访问口令
        </Typography.Paragraph>
        <Form onFinish={onFinish}>
          <Form.Item name="password" rules={[{ required: true, message: '请输入口令' }]}>
            <Input.Password
              size="large"
              prefix={<LockOutlined />}
              placeholder="访问口令"
              autoFocus
            />
          </Form.Item>
          <Button type="primary" htmlType="submit" block size="large" loading={loading}>
            登录
          </Button>
        </Form>
      </Card>
    </div>
  )
}
