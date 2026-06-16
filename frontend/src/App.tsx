import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { Layout } from './components/layout/Layout'
import { useAuthStore } from './store/authStore'

import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import DashboardPage from './pages/DashboardPage'
import ScoringPage from './pages/ScoringPage'
import BatchTestingPage from './pages/BatchTestingPage'
import ReportsPage from './pages/ReportsPage'
import CamerasPage from './pages/CamerasPage'
import TournamentsPage from './pages/TournamentsPage'
import UsersPage from './pages/UsersPage'
import SettingsPage from './pages/SettingsPage'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <BrowserRouter>
      <Toaster 
        position="top-right" 
        toastOptions={{
          style: {
            background: '#0f1629',
            color: '#f1f5f9',
            border: '1px solid #1c2847',
          },
          success: { iconTheme: { primary: '#10b981', secondary: '#0f1629' } },
          error: { iconTheme: { primary: '#ef4444', secondary: '#0f1629' } },
        }} 
      />
      
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        
        <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="scoring" element={<ScoringPage />} />
          <Route path="batch-testing" element={<BatchTestingPage />} />
          <Route path="reports" element={<ReportsPage />} />
          <Route path="cameras" element={<CamerasPage />} />
          <Route path="tournaments" element={<TournamentsPage />} />
          <Route path="users" element={<UsersPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
