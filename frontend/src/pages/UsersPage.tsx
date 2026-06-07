import { UserPlus, Shield, User as UserLogo } from 'lucide-react'

export default function UsersPage() {
  // Placeholder since admin user endpoint not explicitly mapped in requirements yet
  return (
    <div className="p-6 h-full flex flex-col animate-in">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">User Management</h1>
          <p className="text-sm text-slate-500 mt-0.5">Manage system access and roles</p>
        </div>
        <button className="btn-primary flex items-center gap-2">
          <UserPlus className="w-4 h-4" /> Add User
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        <div className="glass-card">
          <table className="w-full text-left text-sm">
            <thead className="text-xs text-slate-500 uppercase bg-navy-900/50">
              <tr>
                <th className="px-6 py-4 rounded-tl-lg">User</th>
                <th className="px-6 py-4">Role</th>
                <th className="px-6 py-4">Status</th>
                <th className="px-6 py-4 rounded-tr-lg text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {/* Mock users */}
              {[
                { name: 'Admin', email: 'admin@archery.local', role: 'admin', active: true },
                { name: 'Scorer 1', email: 'scorer1@archery.local', role: 'scorer', active: true },
                { name: 'Spectator', email: 'guest@archery.local', role: 'spectator', active: false },
              ].map((u, i) => (
                <tr key={i} className="border-t border-navy-700 hover:bg-navy-800/50">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-navy-700 flex items-center justify-center text-slate-400">
                        <UserLogo className="w-4 h-4" />
                      </div>
                      <div>
                        <p className="font-medium text-slate-200">{u.name}</p>
                        <p className="text-xs text-slate-500">{u.email}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span className="flex items-center gap-1.5 text-xs font-medium text-slate-300">
                      {u.role === 'admin' && <Shield className="w-3.5 h-3.5 text-gold-400" />}
                      {u.role}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`px-2.5 py-1 text-xs font-medium rounded-full ${
                      u.active ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' 
                               : 'bg-slate-500/10 text-slate-400 border border-slate-500/20'
                    }`}>
                      {u.active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <button className="text-gold-400 hover:text-gold-300 text-sm font-medium">Edit</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
