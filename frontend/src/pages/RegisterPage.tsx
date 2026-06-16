import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import toast from 'react-hot-toast'
import {
  Crosshair,
  Eye,
  EyeOff,
  Lock,
  User,
  Mail,
  Loader2,
  CheckCircle2,
  XCircle,
} from 'lucide-react'
import { authApi } from '@/api/auth'
import { cn } from '@/lib/utils'

const schema = z
  .object({
    username: z
      .string()
      .min(3, 'Username must be at least 3 characters')
      .max(50, 'Username too long')
      .regex(/^[a-zA-Z0-9_]+$/, 'Only letters, numbers and underscores allowed'),
    email: z.string().email('Invalid email address'),
    password: z
      .string()
      .min(8, 'At least 8 characters')
      .regex(/[A-Z]/, 'Must contain uppercase letter')
      .regex(/[a-z]/, 'Must contain lowercase letter')
      .regex(/[0-9]/, 'Must contain a number')
      .regex(/[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]/, 'Must contain a special character'),
    password_confirm: z.string().min(1, 'Please confirm your password'),
  })
  .refine((d) => d.password === d.password_confirm, {
    message: 'Passwords do not match',
    path: ['password_confirm'],
  })

type FormData = z.infer<typeof schema>

const passwordRules = [
  { label: 'At least 8 characters', regex: /.{8,}/ },
  { label: 'Uppercase letter', regex: /[A-Z]/ },
  { label: 'Lowercase letter', regex: /[a-z]/ },
  { label: 'Number', regex: /[0-9]/ },
  { label: 'Special character (!@#$…)', regex: /[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]/ },
]

export default function RegisterPage() {
  const navigate = useNavigate()
  const [showPass, setShowPass] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [loading, setLoading] = useState(false)

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<FormData>({ resolver: zodResolver(schema) })

  // Track password value for strength indicator
  const passwordValue = watch('password', '')

  const onSubmit = async (data: FormData) => {
    setLoading(true)
    try {
      await authApi.register({
        username: data.username,
        email: data.email,
        password: data.password,
        password_confirm: data.password_confirm,
      })
      toast.success('Account created! Please sign in.')
      navigate('/login')
    } catch (err: any) {
      const msg =
        err?.response?.data?.detail ?? 'Registration failed. Please try again.'
      toast.error(msg)
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

        <div className="space-y-8">
          {/* Target SVG */}
          <div className="flex justify-center">
            <svg width="240" height="240" viewBox="0 0 280 280" className="opacity-80">
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
            </svg>
          </div>

          <div>
            <h1 className="text-3xl font-bold text-slate-100 mb-3">Join ArcheryScore</h1>
            <p className="text-slate-400 leading-relaxed">
              Create your account to access real-time scoring, leaderboards, and tournament management.
            </p>
          </div>

          <div className="space-y-3">
            {[
              '✓ Real-time arrow detection via AI',
              '✓ Live leaderboards & rankings',
              '✓ Multi-format report export (PDF/CSV)',
              '✓ Multi-camera support per lane',
            ].map((f) => (
              <p key={f} className="text-sm text-slate-400">
                {f}
              </p>
            ))}
          </div>
        </div>

        <p className="text-xs text-slate-600">© 2026 Archery Scoring System</p>
      </div>

      {/* Right panel — register form */}
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-sm">
          {/* Mobile logo */}
          <div className="lg:hidden flex items-center gap-3 mb-8">
            <div className="w-8 h-8 rounded-lg bg-gold-500 flex items-center justify-center">
              <Crosshair className="w-5 h-5 text-navy-900" />
            </div>
            <p className="font-bold text-slate-100">ArcheryScore</p>
          </div>

          <div className="mb-6">
            <h2 className="text-2xl font-bold text-slate-100">Create account</h2>
            <p className="text-slate-500 mt-1 text-sm">Fill in the details below to get started</p>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {/* Username */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1.5">Username</label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input
                  {...register('username')}
                  id="register-username"
                  type="text"
                  placeholder="Choose a username"
                  className={cn('input-dark w-full pl-10', errors.username && 'border-red-500/50')}
                />
              </div>
              {errors.username && (
                <p className="text-red-400 text-xs mt-1">{errors.username.message}</p>
              )}
            </div>

            {/* Email */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1.5">Email</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input
                  {...register('email')}
                  id="register-email"
                  type="email"
                  placeholder="your@email.com"
                  className={cn('input-dark w-full pl-10', errors.email && 'border-red-500/50')}
                />
              </div>
              {errors.email && (
                <p className="text-red-400 text-xs mt-1">{errors.email.message}</p>
              )}
            </div>

            {/* Password */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1.5">Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input
                  {...register('password')}
                  id="register-password"
                  type={showPass ? 'text' : 'password'}
                  placeholder="Create a strong password"
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

              {/* Password strength checklist */}
              {passwordValue && (
                <div className="mt-2 space-y-1">
                  {passwordRules.map((rule) => {
                    const ok = rule.regex.test(passwordValue)
                    return (
                      <div key={rule.label} className="flex items-center gap-1.5">
                        {ok ? (
                          <CheckCircle2 className="w-3 h-3 text-emerald-400 flex-shrink-0" />
                        ) : (
                          <XCircle className="w-3 h-3 text-slate-600 flex-shrink-0" />
                        )}
                        <span className={cn('text-xs', ok ? 'text-emerald-400' : 'text-slate-500')}>
                          {rule.label}
                        </span>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>

            {/* Confirm Password */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1.5">
                Confirm Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input
                  {...register('password_confirm')}
                  id="register-password-confirm"
                  type={showConfirm ? 'text' : 'password'}
                  placeholder="Repeat your password"
                  className={cn(
                    'input-dark w-full pl-10 pr-10',
                    errors.password_confirm && 'border-red-500/50'
                  )}
                />
                <button
                  type="button"
                  onClick={() => setShowConfirm(!showConfirm)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                >
                  {showConfirm ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {errors.password_confirm && (
                <p className="text-red-400 text-xs mt-1">{errors.password_confirm.message}</p>
              )}
            </div>

            <button
              id="register-submit"
              type="submit"
              disabled={loading}
              className="w-full btn-primary flex items-center justify-center gap-2 py-2.5 mt-2 disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Creating account...
                </>
              ) : (
                'Create Account'
              )}
            </button>
          </form>

          <div className="mt-5 text-center">
            <p className="text-sm text-slate-500">
              Already have an account?{' '}
              <Link
                to="/login"
                className="text-gold-400 hover:text-gold-300 font-medium transition-colors"
              >
                Sign in
              </Link>
            </p>
          </div>

          <div className="mt-4 p-3 glass-card">
            <p className="text-xs text-slate-500 leading-relaxed">
              <span className="text-slate-400 font-medium">Note:</span> New accounts are created
              with <span className="text-gold-400">spectator</span> role by default. An admin can
              upgrade your role after registration.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
