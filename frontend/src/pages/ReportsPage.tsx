import { useState, useEffect } from 'react'
import { Download, BarChart3, TrendingUp, Image as ImageIcon, Table as TableIcon } from 'lucide-react'
import { useSessionStore } from '@/store/sessionStore'
import { sessionsApi } from '@/api/sessions'
import { reportsApi } from '@/api/health'
import toast from 'react-hot-toast'
import { cn } from '@/lib/utils'
import type { LeaderboardEntry } from '@/types'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line } from 'recharts'

export default function ReportsPage() {
  const { activeSession } = useSessionStore()
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[] | null>(null)
  const [view, setView] = useState<'table' | 'charts' | 'images'>('table')
  const [downloading, setDownloading] = useState(false)

  useEffect(() => {
    if (activeSession) {
      sessionsApi.getLeaderboard(activeSession.id).then(setLeaderboard).catch()
    }
  }, [activeSession])

  const handleDownload = async (format: 'pdf' | 'csv') => {
    if (!activeSession) return
    setDownloading(true)
    try {
      const blob = await reportsApi.generate(activeSession.id, format)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `session_${activeSession.id}_report.${format}`
      document.body.appendChild(a)
      a.click()
      a.remove()
      window.URL.revokeObjectURL(url)
    } catch (err) {
      toast.error(`Failed to download ${format.toUpperCase()}`)
    } finally {
      setDownloading(false)
    }
  }

  if (!activeSession) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8 text-center">
        <BarChart3 className="w-16 h-16 text-slate-700 mb-4" />
        <h2 className="text-xl font-semibold text-slate-200 mb-2">No Active Session</h2>
        <p className="text-slate-500 mb-6">Select an active session to view reports.</p>
      </div>
    )
  }

  // Mock data for charts
  const distributionData = [
    { zone: 'X', count: 12 }, { zone: '10', count: 45 }, { zone: '9', count: 80 },
    { zone: '8', count: 65 }, { zone: '7', count: 30 }, { zone: 'Miss', count: 5 }
  ]

  const trendData = [
    { end: 1, score: 54 }, { end: 2, score: 108 }, { end: 3, score: 164 },
    { end: 4, score: 218 }, { end: 5, score: 275 }, { end: 6, score: 330 }
  ]

  return (
    <div className="p-6 h-full flex flex-col animate-in">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Session Reports</h1>
          <p className="text-sm text-slate-500 mt-0.5">{activeSession.name}</p>
        </div>
        
        <div className="flex gap-2">
          <button 
            onClick={() => handleDownload('csv')} 
            disabled={downloading}
            className="btn-ghost flex items-center gap-2"
          >
            <Download className="w-4 h-4" /> CSV
          </button>
          <button 
            onClick={() => handleDownload('pdf')}
            disabled={downloading}
            className="btn-primary flex items-center gap-2"
          >
            <Download className="w-4 h-4" /> Export PDF
          </button>
        </div>
      </div>

      {/* View Toggles */}
      <div className="flex items-center gap-2 mb-6 bg-navy-800 p-1 rounded-lg w-max border border-navy-700">
        {[
          { id: 'table', icon: TableIcon, label: 'Score Table' },
          { id: 'charts', icon: BarChart3, label: 'Analytics' },
          { id: 'images', icon: ImageIcon, label: 'Gallery' }
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setView(tab.id as any)}
            className={cn(
              "flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors",
              view === tab.id ? "bg-navy-600 text-slate-100 shadow" : "text-slate-400 hover:text-slate-200"
            )}
          >
            <tab.icon className="w-4 h-4" /> {tab.label}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto min-h-0 glass-card p-6">
        {view === 'table' && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-xs text-slate-500 uppercase bg-navy-900/50">
                <tr>
                  <th className="px-4 py-3 rounded-tl-lg">Rank</th>
                  <th className="px-4 py-3">Archer</th>
                  <th className="px-4 py-3">Lane</th>
                  <th className="px-4 py-3">Total</th>
                  <th className="px-4 py-3">R1</th>
                  <th className="px-4 py-3">R2</th>
                  <th className="px-4 py-3 rounded-tr-lg">R3</th>
                </tr>
              </thead>
              <tbody>
                {leaderboard?.map(entry => (
                  <tr key={entry.archer_id} className="border-b border-navy-700 hover:bg-navy-800/50">
                    <td className="px-4 py-3 font-medium text-slate-300">{entry.rank}</td>
                    <td className="px-4 py-3 font-medium text-slate-200">{entry.archer_name}</td>
                    <td className="px-4 py-3 text-slate-400">{entry.lane_number}</td>
                    <td className="px-4 py-3 font-bold text-gold-400">{entry.total_score}</td>
                    <td className="px-4 py-3 text-slate-300">{entry.round_1_score ?? '-'}</td>
                    <td className="px-4 py-3 text-slate-300">{entry.round_2_score ?? '-'}</td>
                    <td className="px-4 py-3 text-slate-300">{entry.round_3_score ?? '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {view === 'charts' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 h-[400px]">
            <div className="flex flex-col">
              <h3 className="text-lg font-semibold text-slate-200 mb-4 flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-blue-400" /> Score Distribution
              </h3>
              <div className="flex-1">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={distributionData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1c2847" />
                    <XAxis dataKey="zone" stroke="#94a3b8" />
                    <YAxis stroke="#94a3b8" />
                    <Tooltip cursor={{fill: '#1c2847'}} contentStyle={{backgroundColor: '#0f1629', borderColor: '#1c2847', color: '#f1f5f9'}} />
                    <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="flex flex-col">
              <h3 className="text-lg font-semibold text-slate-200 mb-4 flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-emerald-400" /> Average Progression
              </h3>
              <div className="flex-1">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={trendData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1c2847" />
                    <XAxis dataKey="end" stroke="#94a3b8" />
                    <YAxis stroke="#94a3b8" />
                    <Tooltip contentStyle={{backgroundColor: '#0f1629', borderColor: '#1c2847', color: '#f1f5f9'}} />
                    <Line type="monotone" dataKey="score" stroke="#10b981" strokeWidth={3} dot={{r: 4, fill: '#10b981'}} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        )}

        {view === 'images' && (
          <div className="text-center py-12 text-slate-500">
            <ImageIcon className="w-12 h-12 mx-auto mb-4 opacity-50" />
            <p>Image gallery feature coming soon.</p>
          </div>
        )}
      </div>
    </div>
  )
}
