import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import toast from 'react-hot-toast'
import { Crosshair, Eye, EyeOff, Lock, User, Loader2 } from 'lucide-react'
import { authApi } from '@/api/auth'
import { useAuthStore } from '@/store/authStore'
import { cn } from '@/lib/utils'

const schema = z.object({
  username: z.string().min(3, 'Username required'),
  password: z.string().min(1, 'Password required'),
})

type FormData = z.infer<typeof schema>

export default function LoginPage() {
  const navigate = useNavigate()
  const setAuth = useAuthStore((s) => s.setAuth)
  const [showPass, setShowPass] = useState(false)
  const [loading, setLoading] = useState(false)

  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
  })

  const onSubmit = async (data: FormData) => {
    setLoading(true)
    try {
      const res = await authApi.login(data)
      // Decode user from JWT (basic decode)
      const payload = JSON.parse(atob(res.access_token.split('.')[1]))
      setAuth(
        { id: payload.sub, username: data.username, email: '', role: payload.role ?? 'archer', is_active: true, created_at: '' },
        res.access_token,
        res.refresh_token
      )
      toast.success('Welcome back!')
      navigate('/dashboard')
    } catch {
      toast.error('Invalid username or password')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-navy-950 flex">
      {/* Left panel — branding */}
      <div className="hidden lg:flex flex-col justify-between w-1/2 bg-navy-900 border-r border-navy-700 p-12">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gold-500 flex items-center justify-center">
            <Crosshair className="w-6 h-6 text-navy-900" />
          </div>
          <div>
            <p className="text-lg font-bold text-slate-100">ArcheryScore</p>
            <p className="text-xs text-slate-500">Automated Scoring System</p>
          </div>
        </div>

        <div className="space-y-6">
          {/* Target SVG illustration */}
          <div className="flex justify-center">
            <svg width="280" height="280" viewBox="0 0 280 280" className="opacity-80">
              <circle cx="140" cy="140" r="130" fill="none" stroke="#1c2847" strokeWidth="2" />
              <circle cx="140" cy="140" r="117" fill="#1a1a2e" stroke="#243358" strokeWidth="1.5" />
              <circle cx="140" cy="140" r="104" fill="#1c2232" stroke="#2d3a5e" strokeWidth="1.5" />
              <circle cx="140" cy="140" r="91" fill="#1e2740" stroke="#243558" strokeWidth="1.5" />
              <circle cx="140" cy="140" r="78" fill="none" stroke="#1e3a5f" strokeWidth="1.5" />
              <circle cx="140" cy="140" r="65" fill="none" stroke="#1e4080" strokeWidth="1.5" />
              <circle cx="140" cy="140" r="52" fill="none" stroke="#1a3a70" strokeWidth="2" />
              <circle cx="140" cy="140" r="39" fill="none" stroke="#8b1a1a" strokeWidth="2" />
              <circle cx="140" cy="140" r="26" fill="#991f1f" stroke="#c0392b" strokeWidth="2" />
              <circle cx="140" cy="140" r="13" fill="#f59e0b" stroke="#d97706" strokeWidth="2" />
              <circle cx="140" cy="140" r="5" fill="#fcd34d" />
              {/* Arrows */}
              <circle cx="140" cy="127" r="3" fill="#10b981" stroke="#059669" strokeWidth="1.5" />
              <circle cx="152" cy="143" r="3" fill="#10b981" stroke="#059669" strokeWidth="1.5" />
              <circle cx="133" cy="148" r="3" fill="#f59e0b" stroke="#d97706" strokeWidth="1.5" />
            </svg>
          </div>

          <div>
            <h1 className="text-3xl font-bold text-slate-100 mb-3">
              AI-Powered Archery Scoring
            </h1>
            <p className="text-slate-400 leading-relaxed">
              Real-time arrow detection, live leaderboards, and multi-format report generation.
              Eliminate manual scoring errors with computer vision.
            </p>
          </div>

          <div className="grid grid-cols-3 gap-4">
            {[
              { value: '<1s', label: 'Scoring Time' },
              { value: '95%+', label: 'Ring Detection' },
              { value: '26', label: 'API Endpoints' },
            ].map((stat) => (
              <div key={stat.label} className="glass-card p-4 text-center">
                <p className="text-2xl font-bold gold-text">{stat.value}</p>
                <p className="text-xs text-slate-500 mt-1">{stat.label}</p>
              </div>
            ))}
          </div>
        </div>

        <p className="text-xs text-slate-600">© 2026 Archery Scoring System — AIDLC Generated</p>
      </div>

      {/* Right panel — login form */}
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-sm">
          <div className="lg:hidden flex items-center gap-3 mb-8">
            <div className="w-8 h-8 rounded-lg bg-gold-500 flex items-center justify-center">
              <Crosshair className="w-5 h-5 text-navy-900" />
            </div>
            <p className="font-bold text-slate-100">ArcheryScore</p>
          </div>

          <div className="mb-8">
            <h2 className="text-2xl font-bold text-slate-100">Sign in</h2>
            <p className="text-slate-500 mt-1 text-sm">Enter your credentials to continue</p>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1.5">Username</label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input
                  {...register('username')}
                  id="username"
                  type="text"
                  placeholder="Enter your username"
                  className={cn('input-dark w-full pl-10', errors.username && 'border-red-500/50')}
                />
              </div>
              {errors.username && (
                <p className="text-red-400 text-xs mt-1">{errors.username.message}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1.5">Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input
                  {...register('password')}
                  id="password"
                  type={showPass ? 'text' : 'password'}
                  placeholder="Enter your password"
                  className={cn('input-dark w-full pl-10 pr-10', errors.password && 'border-red-500/50')}
                />
                <button
                  type="button"
                  onClick={() => setShowPass(!showPass)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                >
                  {showPass ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {errors.password && (
                <p className="text-red-400 text-xs mt-1">{errors.password.message}</p>
              )}
            </div>

            <button
              id="login-submit"
              type="submit"
              disabled={loading}
              className="w-full btn-primary flex items-center justify-center gap-2 py-2.5 disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Signing in...
                </>
              ) : (
                'Sign In'
              )}
            </button>
          </form>

          <div className="mt-6 p-4 glass-card">
            <p className="text-xs text-slate-500 font-medium mb-2">Demo credentials:</p>
            <div className="space-y-1">
              <p className="text-xs text-slate-400"><span className="text-gold-400">admin</span> / admin123!</p>
              <p className="text-xs text-slate-400"><span className="text-gold-400">scorer</span> / scorer123!</p>
            </div>
          </div>

          <div className="mt-4 text-center">
            <p className="text-sm text-slate-500">
              Don't have an account?{' '}
              <Link
                to="/register"
                className="text-gold-400 hover:text-gold-300 font-medium transition-colors"
              >
                Create one
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
