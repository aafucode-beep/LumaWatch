import { HashRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { tokenStore } from './api/client'
import AppLayout from './layout/AppLayout'
import LoginPage from './pages/LoginPage'
import CompaniesPage from './pages/CompaniesPage'
import CompanyDetailPage from './pages/CompanyDetailPage'
import ProbePage from './pages/ProbePage'
import TagsPage from './pages/TagsPage'

function RequireAuth({ children }: { children: JSX.Element }) {
  const location = useLocation()
  if (!tokenStore.get()) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }
  return children
}

export default function App() {
  return (
    <HashRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            <RequireAuth>
              <AppLayout />
            </RequireAuth>
          }
        >
          <Route index element={<CompaniesPage />} />
          <Route path="companies/:id" element={<CompanyDetailPage />} />
          <Route path="probe" element={<ProbePage />} />
          <Route path="tags" element={<TagsPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </HashRouter>
  )
}
