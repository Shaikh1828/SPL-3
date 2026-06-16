import { useState, useEffect, useCallback } from 'react'
import {
  UserPlus, Shield, User as UserIcon, Search, RefreshCw,
  ToggleLeft, ToggleRight, Trash2, Edit3, X, Check, AlertCircle,
} from 'lucide-react'
import { usersApi } from '@/api/users'
import { useAuthStore } from '@/store/authStore'
import toast from 'react-hot-toast'
import { cn } from '@/lib/utils'
import type { User, UserRole } from '@/types'

// ─── Role badge ──────────────────────────────────────────────────────────────
const ROLE_STYLES: Record<UserRole, string> = {
  admin:     'bg-gold-500/10 text-gold-400 border-gold-500/20',
  scorer:    'bg-blue-500/10 text-blue-400 border-blue-500/20',
  spectator: 'bg-slate-500/10 text-slate-400 border-slate-500/20',
  archer:    'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
}

function RoleBadge({ role }: { role: UserRole }) {
  return (
    <span className={cn('px-2.5 py-1 text-xs font-medium rounded-full border flex items-center gap-1 w-fit', ROLE_STYLES[role])}>
      {role === 'admin' && <Shield className="w-3 h-3" />}
      {role}
    </span>
  )
}

// ─── Add User Modal ───────────────────────────────────────────────────────────
interface AddUserModalProps { onClose: () => void; onSuccess: () => void }

function AddUserModal({ onClose, onSuccess }: AddUserModalProps) {
  const [form, setForm] = useState({ username: '', email: '', password: '', role: 'spectator' as UserRole })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await usersApi.create(form)
      toast.success(`User '${form.username}' created`)
      onSuccess()
      onClose()
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Failed to create user')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="glass-card w-full max-w-md p-6 animate-in">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-bold text-slate-100">Add New User</h2>
          <button onClick={onClose} className="btn-ghost p-1.5 rounded-lg"><X className="w-4 h-4" /></button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-400 mb-1.5">Username</label>
            <input
              className="input-dark w-full"
              placeholder="e.g. john_scorer"
              value={form.username}
              onChange={(e) => setForm({ ...form, username: e.target.value })}
              required minLength={3}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-400 mb-1.5">Email</label>
            <input
              type="email" className="input-dark w-full"
              placeholder="john@archery.local"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-400 mb-1.5">Password</label>
            <input
              type="password" className="input-dark w-full"
              placeholder="Min 8 characters"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              required minLength={8}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-400 mb-1.5">Role</label>
            <select
              className="input-dark w-full"
              value={form.role}
              onChange={(e) => setForm({ ...form, role: e.target.value as UserRole })}
            >
              <option value="spectator">Spectator — Read-only</option>
              <option value="scorer">Scorer — Record scores</option>
              <option value="archer">Archer — View own scores</option>
              <option value="admin">Admin — Full access</option>
            </select>
          </div>

          {error && (
            <div className="flex items-center gap-2 text-red-400 text-sm bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              {error}
            </div>
          )}

          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="btn-ghost flex-1">Cancel</button>
            <button type="submit" disabled={loading} className="btn-primary flex-1 flex items-center justify-center gap-2">
              {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <UserPlus className="w-4 h-4" />}
              Create User
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ─── Inline Edit Row ──────────────────────────────────────────────────────────
interface EditRowProps { user: User; onSave: (u: User) => void; onCancel: () => void }

function EditRow({ user, onSave, onCancel }: EditRowProps) {
  const [role, setRole] = useState<UserRole>(user.role)
  const [isActive, setIsActive] = useState(user.is_active)
  const [loading, setLoading] = useState(false)

  const handleSave = async () => {
    setLoading(true)
    try {
      const updated = await usersApi.update(user.id, { role, is_active: isActive })
      toast.success('User updated')
      onSave(updated)
    } catch {
      toast.error('Update failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <tr className="border-t border-navy-700 bg-navy-800/70">
      <td className="px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-gold-500/20 flex items-center justify-center">
            <UserIcon className="w-4 h-4 text-gold-400" />
          </div>
          <div>
            <p className="font-medium text-slate-200">{user.username}</p>
            <p className="text-xs text-slate-500">{user.email}</p>
          </div>
        </div>
      </td>
      <td className="px-6 py-4">
        <select
          className="input-dark text-xs py-1"
          value={role}
          onChange={(e) => setRole(e.target.value as UserRole)}
        >
          <option value="spectator">spectator</option>
          <option value="scorer">scorer</option>
          <option value="archer">archer</option>
          <option value="admin">admin</option>
        </select>
      </td>
      <td className="px-6 py-4">
        <button onClick={() => setIsActive(!isActive)} className="flex items-center gap-2 text-sm">
          {isActive
            ? <ToggleRight className="w-5 h-5 text-emerald-400" />
            : <ToggleLeft className="w-5 h-5 text-slate-500" />}
          <span className={isActive ? 'text-emerald-400' : 'text-slate-500'}>
            {isActive ? 'Active' : 'Inactive'}
          </span>
        </button>
      </td>
      <td className="px-6 py-4 text-right">
        <div className="flex items-center justify-end gap-2">
          <button onClick={onCancel} className="btn-ghost p-1.5 text-slate-400 hover:text-slate-200 rounded">
            <X className="w-4 h-4" />
          </button>
          <button onClick={handleSave} disabled={loading} className="btn-primary py-1 px-3 text-sm flex items-center gap-1">
            {loading ? <RefreshCw className="w-3 h-3 animate-spin" /> : <Check className="w-3 h-3" />}
            Save
          </button>
        </div>
      </td>
    </tr>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────
export default function UsersPage() {
  const { user: currentUser } = useAuthStore()
  const [users, setUsers] = useState<User[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [showAddModal, setShowAddModal] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [search, setSearch] = useState('')
  const [roleFilter, setRoleFilter] = useState('')
  const [activeFilter, setActiveFilter] = useState<boolean | undefined>(undefined)

  const isAdmin = currentUser?.role === 'admin'

  const loadUsers = useCallback(async () => {
    setLoading(true)
    try {
      const res = await usersApi.list({
        role: roleFilter || undefined,
        is_active: activeFilter,
        limit: 100,
      })
      const list = Array.isArray(res) ? res : (res && Array.isArray(res.items) ? res.items : [])
      setUsers(list)
      setTotal(Array.isArray(res) ? res.length : (res?.total ?? 0))
    } catch {
      toast.error('Failed to load users')
    } finally {
      setLoading(false)
    }
  }, [roleFilter, activeFilter])

  useEffect(() => { loadUsers() }, [loadUsers])

  const handleDeactivate = async (user: User) => {
    if (!window.confirm(`Deactivate '${user.username}'?`)) return
    try {
      await usersApi.deactivate(user.id)
      toast.success(`'${user.username}' deactivated`)
      loadUsers()
    } catch {
      toast.error('Failed to deactivate')
    }
  }

  const filtered = users.filter(
    (u) =>
      !search ||
      u.username.toLowerCase().includes(search.toLowerCase()) ||
      u.email.toLowerCase().includes(search.toLowerCase()),
  )

  return (
    <div className="p-6 h-full flex flex-col animate-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">User Management</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            {total} registered user{total !== 1 ? 's' : ''} · Admin-only panel
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={loadUsers} disabled={loading} className="btn-ghost flex items-center gap-2 text-sm">
            <RefreshCw className={cn('w-4 h-4', loading && 'animate-spin')} />
          </button>
          {isAdmin && (
            <button onClick={() => setShowAddModal(true)} className="btn-primary flex items-center gap-2">
              <UserPlus className="w-4 h-4" /> Add User
            </button>
          )}
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-4">
        <div className="relative flex-1 min-w-48">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
          <input
            className="input-dark w-full pl-9 text-sm"
            placeholder="Search by username or email…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <select
          className="input-dark text-sm"
          value={roleFilter}
          onChange={(e) => setRoleFilter(e.target.value)}
        >
          <option value="">All roles</option>
          <option value="admin">Admin</option>
          <option value="scorer">Scorer</option>
          <option value="archer">Archer</option>
          <option value="spectator">Spectator</option>
        </select>
        <select
          className="input-dark text-sm"
          value={activeFilter === undefined ? '' : String(activeFilter)}
          onChange={(e) =>
            setActiveFilter(e.target.value === '' ? undefined : e.target.value === 'true')
          }
        >
          <option value="">All statuses</option>
          <option value="true">Active only</option>
          <option value="false">Inactive only</option>
        </select>
      </div>

      {/* Table */}
      <div className="flex-1 overflow-y-auto">
        <div className="glass-card">
          {!isAdmin && (
            <div className="flex items-center gap-2 text-amber-400 text-sm bg-amber-500/10 border-b border-amber-500/20 px-6 py-3">
              <AlertCircle className="w-4 h-4" />
              You need admin privileges to manage users.
            </div>
          )}
          <table className="w-full text-left text-sm">
            <thead className="text-xs text-slate-500 uppercase bg-navy-900/50">
              <tr>
                <th className="px-6 py-4 rounded-tl-lg">User</th>
                <th className="px-6 py-4">Role</th>
                <th className="px-6 py-4">Status</th>
                <th className="px-6 py-4">Joined</th>
                <th className="px-6 py-4 rounded-tr-lg text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center text-slate-500">
                    <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2" />
                    Loading users…
                  </td>
                </tr>
              )}

              {!loading && filtered.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center text-slate-500">
                    No users found
                  </td>
                </tr>
              )}

              {!loading &&
                filtered.map((u) =>
                  editingId === u.id ? (
                    <EditRow
                      key={u.id}
                      user={u}
                      onSave={(updated) => {
                        setUsers((prev) => prev.map((x) => (x.id === updated.id ? updated : x)))
                        setEditingId(null)
                      }}
                      onCancel={() => setEditingId(null)}
                    />
                  ) : (
                    <tr key={u.id} className="border-t border-navy-700 hover:bg-navy-800/40 transition-colors">
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className={cn(
                            'w-8 h-8 rounded-full flex items-center justify-center',
                            u.role === 'admin' ? 'bg-gold-500/20' : 'bg-navy-700',
                          )}>
                            {u.role === 'admin'
                              ? <Shield className="w-4 h-4 text-gold-400" />
                              : <UserIcon className="w-4 h-4 text-slate-400" />}
                          </div>
                          <div>
                            <p className="font-medium text-slate-200">{u.username}
                              {u.id === currentUser?.id && (
                                <span className="ml-2 text-xs text-gold-400 font-normal">(you)</span>
                              )}
                            </p>
                            <p className="text-xs text-slate-500">{u.email}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4"><RoleBadge role={u.role} /></td>
                      <td className="px-6 py-4">
                        <span className={cn(
                          'px-2.5 py-1 text-xs font-medium rounded-full border',
                          u.is_active
                            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                            : 'bg-slate-500/10 text-slate-500 border-slate-600/20',
                        )}>
                          {u.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-xs text-slate-500">
                        {new Date(u.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 text-right">
                        {isAdmin && u.id !== currentUser?.id && (
                          <div className="flex items-center justify-end gap-2">
                            <button
                              onClick={() => setEditingId(u.id)}
                              className="btn-ghost p-1.5 rounded text-slate-400 hover:text-gold-400"
                              title="Edit role / status"
                            >
                              <Edit3 className="w-4 h-4" />
                            </button>
                            {u.is_active && (
                              <button
                                onClick={() => handleDeactivate(u)}
                                className="btn-ghost p-1.5 rounded text-slate-400 hover:text-red-400"
                                title="Deactivate user"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            )}
                          </div>
                        )}
                      </td>
                    </tr>
                  ),
                )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add User Modal */}
      {showAddModal && (
        <AddUserModal
          onClose={() => setShowAddModal(false)}
          onSuccess={loadUsers}
        />
      )}
    </div>
  )
}
