import { Layout, Menu, Button, Typography } from 'antd'
import {
  DatabaseOutlined,
  RadarChartOutlined,
  TagsOutlined,
  LogoutOutlined,
} from '@ant-design/icons'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { tokenStore } from '../api/client'

const { Header, Content, Sider } = Layout

export default function AppLayout() {
  const navigate = useNavigate()
  const location = useLocation()

  const selectedKey = location.pathname.startsWith('/probe')
    ? 'probe'
    : location.pathname.startsWith('/tags')
      ? 'tags'
      : 'companies'

  const logout = () => {
    tokenStore.clear()
    navigate('/login', { replace: true })
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ display: 'flex', alignItems: 'center', paddingInline: 16 }}>
        <Typography.Title level={4} style={{ color: '#fff', margin: 0, flex: 1 }}>
          建筑照明网站情报库
        </Typography.Title>
        <Button icon={<LogoutOutlined />} onClick={logout} ghost>
          退出
        </Button>
      </Header>
      <Layout>
        <Sider breakpoint="lg" collapsedWidth="0" width={180} theme="light">
          <Menu
            mode="inline"
            selectedKeys={[selectedKey]}
            style={{ height: '100%', borderRight: 0 }}
            onClick={({ key }) => {
              if (key === 'companies') navigate('/')
              else navigate(`/${key}`)
            }}
            items={[
              { key: 'companies', icon: <DatabaseOutlined />, label: '企业库' },
              { key: 'probe', icon: <RadarChartOutlined />, label: '探测工作台' },
              { key: 'tags', icon: <TagsOutlined />, label: '标签管理' },
            ]}
          />
        </Sider>
        <Content style={{ padding: 16, overflow: 'auto' }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
