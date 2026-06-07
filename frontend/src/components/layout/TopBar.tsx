import { Bell, LogOut, User, ChevronDown, Activity } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import { useSessionStore } from '@/store/sessionStore'

export function TopBar() {
  const { user, logout } = useAuthStore()
  const { activeSession } = useSessionStore()
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <header className="h-14 bg-navy-900 border-b border-navy-700 flex items-center justify-between px-6">
      {/* Active session pill */}
      <div className="flex items-center gap-3">
        {activeSession ? (
          <div className="flex items-center gap-2 bg-emerald-500/10 border border-emerald-500/20 rounded-full px-3 py-1">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-xs font-medium text-emerald-400">
              Live: {activeSession.name}
            </span>
          </div>
        ) : (
          <div className="flex items-center gap-2 bg-slate-500/10 border border-slate-500/20 rounded-full px-3 py-1">
            <Activity className="w-3 h-3 text-slate-500" />
            <span className="text-xs text-slate-500">No Active Session</span>
          </div>
        )}
      </div>

      {/* Right actions */}
      <div className="flex items-center gap-2">
        <button className="btn-ghost relative">
          <Bell className="w-4 h-4" />
        </button>

        {/* User menu */}
        <div className="relative">
          <button
            onClick={() => setMenuOpen(!menuOpen)}
            className="flex items-center gap-2 btn-ghost"
          >
            <div className="w-7 h-7 rounded-full bg-gold-500/20 border border-gold-500/30 flex items-center justify-center">
              <User className="w-3.5 h-3.5 text-gold-400" />
            </div>
            <span className="text-sm font-medium text-slate-200">{user?.username}</span>
            <ChevronDown className="w-3 h-3 text-slate-500" />
          </button>

          {menuOpen && (
            <div className="absolute right-0 top-full mt-2 w-48 glass-card shadow-xl z-50 py-1 animate-in">
              <div className="px-3 py-2 border-b border-navy-700">
                <p className="text-xs text-slate-500">Signed in as</p>
                <p className="text-sm font-medium text-slate-200">{user?.email}</p>
                <span className="inline-block mt-1 text-xs bg-gold-500/20 text-gold-400 border border-gold-500/30 rounded-full px-2 py-0.5">
                  {user?.role}
                </span>
              </div>
              <button
                onClick={handleLogout}
                className="w-full flex items-center gap-2 px-3 py-2 text-sm text-red-400 hover:bg-red-500/10 transition-colors"
              >
                <LogOut className="w-4 h-4" />
                Sign out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
