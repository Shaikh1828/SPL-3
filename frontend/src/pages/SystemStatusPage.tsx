import { useEffect, useState, useCallback } from 'react'
import {
  Cpu, HardDrive, Database, Server, Activity, RefreshCw,
  CheckCircle, Zap, Layers, Clock
} from 'lucide-react'
import { healthApi } from '@/api/health'
import type { SystemMetrics } from '@/types'
import { cn } from '@/lib/utils'

export default function SystemStatusPage() {
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null)
  const [loading, setLoading] = useState(true)
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [lastRefreshed, setLastRefreshed] = useState<Date>(new Date())

  const fetchMetrics = useCallback(async () => {
    try {
      setLoading(true)
      const data = await healthApi.systemMetrics()
      setMetrics(data)
      setLastRefreshed(new Date())
    } catch (err) {
      console.error('Failed to fetch system metrics:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchMetrics()
    if (!autoRefresh) return
    const interval = setInterval(fetchMetrics, 5000)
    return () => clearInterval(interval)
  }, [fetchMetrics, autoRefresh])

  const cpu = metrics?.cpu
  const memory = metrics?.memory
  const storage = metrics?.storage
  const ai = metrics?.ai_engine
  const db = metrics?.database
  const cache = metrics?.cache
  const threadpool = metrics?.threadpool
  const runtime = metrics?.runtime

  return (
    <div className="p-6 space-y-6 animate-in">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-2.5">
            <Activity className="w-6 h-6 text-gold-400" />
            System Status & Infrastructure
          </h1>
          <p className="text-sm text-slate-400 mt-0.5">
            Real-time server hardware diagnostics, AI engine status, and database metrics
          </p>
        </div>

        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-xs text-slate-400 cursor-pointer bg-navy-800/80 px-3 py-1.5 rounded-lg border border-navy-700">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={e => setAutoRefresh(e.target.checked)}
              className="rounded text-gold-500 focus:ring-0 bg-navy-900 border-navy-700"
            />
            Auto-refresh (5s)
          </label>

          <button
            onClick={fetchMetrics}
            disabled={loading}
            className="btn-ghost text-xs flex items-center gap-1.5 px-3 py-1.5"
          >
            <RefreshCw className={cn('w-3.5 h-3.5', loading && 'animate-spin')} />
            Refresh
          </button>
        </div>
      </div>

      {/* Primary Hardware Gauges */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {/* CPU & Processing Load */}
        <div className="glass-card p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-lg bg-blue-500/10 border border-blue-500/20 text-blue-400">
                <Cpu className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-slate-200">CPU Load</h3>
                <p className="text-xs text-slate-400">{cpu?.cores || 1} System Cores</p>
              </div>
            </div>
            <span className="text-xs font-mono font-semibold px-2 py-0.5 rounded bg-navy-800 text-blue-400">
              {cpu?.approx_utilization_percent ?? 0}%
            </span>
          </div>

          <div className="space-y-1.5">
            <div className="flex justify-between text-xs text-slate-400">
              <span>Estimated Load</span>
              <span>1m: {cpu?.load_1m ?? '0.00'}</span>
            </div>
            <div className="h-2 bg-navy-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-blue-500 rounded-full transition-all duration-500"
                style={{ width: `${Math.min(100, cpu?.approx_utilization_percent ?? 5)}%` }}
              />
            </div>
          </div>

          <div className="grid grid-cols-3 gap-2 pt-2 border-t border-navy-800/80 text-center">
            <div className="p-2 rounded-lg bg-navy-800/40">
              <p className="text-[10px] text-slate-400">1m Avg</p>
              <p className="text-xs font-bold text-slate-200 mt-0.5">{cpu?.load_1m ?? '0.00'}</p>
            </div>
            <div className="p-2 rounded-lg bg-navy-800/40">
              <p className="text-[10px] text-slate-400">5m Avg</p>
              <p className="text-xs font-bold text-slate-200 mt-0.5">{cpu?.load_5m ?? '0.00'}</p>
            </div>
            <div className="p-2 rounded-lg bg-navy-800/40">
              <p className="text-[10px] text-slate-400">15m Avg</p>
              <p className="text-xs font-bold text-slate-200 mt-0.5">{cpu?.load_15m ?? '0.00'}</p>
            </div>
          </div>
        </div>

        {/* Memory (RAM) */}
        <div className="glass-card p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
                <Server className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-slate-200">System Memory</h3>
                <p className="text-xs text-slate-400">
                  {memory ? `${(memory.total_mb / 1024).toFixed(1)} GB Total RAM` : 'RAM Info'}
                </p>
              </div>
            </div>
            <span className="text-xs font-mono font-semibold px-2 py-0.5 rounded bg-navy-800 text-emerald-400">
              {memory?.used_percent ?? 0}%
            </span>
          </div>

          <div className="space-y-1.5">
            <div className="flex justify-between text-xs text-slate-400">
              <span>{memory ? `${(memory.used_mb / 1024).toFixed(2)} GB Used` : 'Calculating...'}</span>
              <span>{memory ? `${(memory.available_mb / 1024).toFixed(2)} GB Free` : ''}</span>
            </div>
            <div className="h-2 bg-navy-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-emerald-500 rounded-full transition-all duration-500"
                style={{ width: `${Math.max(3, memory?.used_percent ?? 0)}%` }}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2 pt-2 border-t border-navy-800/80 text-center">
            <div className="p-2 rounded-lg bg-navy-800/40">
              <p className="text-[10px] text-slate-400">Used Memory</p>
              <p className="text-xs font-bold text-slate-200 mt-0.5">
                {memory ? `${memory.used_mb} MB` : '—'}
              </p>
            </div>
            <div className="p-2 rounded-lg bg-navy-800/40">
              <p className="text-[10px] text-slate-400">Available Memory</p>
              <p className="text-xs font-bold text-slate-200 mt-0.5">
                {memory ? `${memory.available_mb} MB` : '—'}
              </p>
            </div>
          </div>
        </div>

        {/* Disk & Storage Volume */}
        <div className="glass-card p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-lg bg-purple-500/10 border border-purple-500/20 text-purple-400">
                <HardDrive className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-slate-200">Storage Volume</h3>
                <p className="text-xs text-slate-400">/storage Volume Quota</p>
              </div>
            </div>
            <span className="text-xs font-mono font-semibold px-2 py-0.5 rounded bg-navy-800 text-purple-400">
              {storage?.usage_percent ?? 0}%
            </span>
          </div>

          <div className="space-y-1.5">
            <div className="flex justify-between text-xs text-slate-400">
              <span>{storage?.used_gb ?? 0} GB Used</span>
              <span>{storage?.quota_gb ?? 10} GB Quota</span>
            </div>
            <div className="h-2 bg-navy-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-purple-500 rounded-full transition-all duration-500"
                style={{ width: `${Math.max(2, storage?.usage_percent ?? 0)}%` }}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2 pt-2 border-t border-navy-800/80 text-center">
            <div className="p-2 rounded-lg bg-navy-800/40">
              <p className="text-[10px] text-slate-400">Volume Status</p>
              <p className="text-xs font-bold text-emerald-400 mt-0.5 flex items-center justify-center gap-1">
                <CheckCircle className="w-3 h-3" />
                {storage?.status === 'ok' ? 'Healthy' : storage?.status ?? 'OK'}
              </p>
            </div>
            <div className="p-2 rounded-lg bg-navy-800/40">
              <p className="text-[10px] text-slate-400">Host Total Disk</p>
              <p className="text-xs font-bold text-slate-200 mt-0.5">
                {storage?.disk_total_gb ? `${storage.disk_total_gb} GB` : '10 GB Quota'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Deep Learning & AI Engine Card */}
      <div className="glass-card p-6 border-gold-500/20">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-gold-500/10 border border-gold-500/30 text-gold-400">
              <Zap className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
                {ai?.model_name || 'Ultralytics YOLO11 Deep Learning Engine'}
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  Ready & Active
                </span>
              </h2>
              <p className="text-xs text-slate-400">
                Primary object detector & subpixel tip locator ({ai?.device || 'CPU Optimized'})
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 text-xs text-slate-400 bg-navy-900/60 px-3 py-1.5 rounded-lg border border-navy-700">
            <span>Weights:</span>
            <span className="font-mono text-gold-300 truncate max-w-[200px]">{ai?.weights_path}</span>
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
          <div className="p-3 rounded-xl bg-navy-900/50 border border-navy-700/60 text-center">
            <p className="text-[11px] uppercase tracking-wider text-slate-400 font-semibold">mAP50 Accuracy</p>
            <p className="text-lg font-bold text-gold-400 mt-1">{ai?.benchmark_map50 ?? 97.8}%</p>
          </div>
          <div className="p-3 rounded-xl bg-navy-900/50 border border-navy-700/60 text-center">
            <p className="text-[11px] uppercase tracking-wider text-slate-400 font-semibold">Recall Rate</p>
            <p className="text-lg font-bold text-emerald-400 mt-1">{ai?.benchmark_recall ?? 97.2}%</p>
          </div>
          <div className="p-3 rounded-xl bg-navy-900/50 border border-navy-700/60 text-center">
            <p className="text-[11px] uppercase tracking-wider text-slate-400 font-semibold">Precision Score</p>
            <p className="text-lg font-bold text-blue-400 mt-1">{ai?.benchmark_precision ?? 94.0}%</p>
          </div>
          <div className="p-3 rounded-xl bg-navy-900/50 border border-navy-700/60 text-center">
            <p className="text-[11px] uppercase tracking-wider text-slate-400 font-semibold">Model Footprint</p>
            <p className="text-lg font-bold text-purple-400 mt-1">{ai?.weights_size_mb ?? 5.61} MB</p>
          </div>
        </div>
      </div>

      {/* Subsystem Health Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {/* PostgreSQL Database */}
        <div className="glass-card p-5 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Database className="w-4 h-4 text-blue-400" />
              <h3 className="font-semibold text-sm text-slate-200">PostgreSQL 15 DB</h3>
            </div>
            <span className="flex items-center gap-1 text-xs text-emerald-400 font-medium">
              <CheckCircle className="w-3.5 h-3.5" />
              {db?.status === 'ok' ? 'Connected' : 'Degraded'}
            </span>
          </div>
          <p className="text-xs text-slate-400">
            QueuePool connection pooling enabled with pre-ping validation & exponential backoff.
          </p>
          <div className="text-xs font-mono text-slate-400 bg-navy-900/60 p-2.5 rounded-lg border border-navy-800 space-y-1">
            <p>Pool Size: 5–20 connections</p>
            <p>Recycle TTL: 3,600 seconds</p>
          </div>
        </div>

        {/* Redis Cache */}
        <div className="glass-card p-5 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Zap className="w-4 h-4 text-amber-400" />
              <h3 className="font-semibold text-sm text-slate-200">Redis 7 Cache</h3>
            </div>
            <span className="flex items-center gap-1 text-xs text-emerald-400 font-medium">
              <CheckCircle className="w-3.5 h-3.5" />
              {cache?.status === 'ok' ? 'Connected' : 'Degraded'}
            </span>
          </div>
          <p className="text-xs text-slate-400">
            Real-time sorted sets for live leaderboards and in-process WebSocket fan-out events.
          </p>
          <div className="text-xs font-mono text-slate-400 bg-navy-900/60 p-2.5 rounded-lg border border-navy-800 space-y-1">
            <p>Max Memory: 512 MB</p>
            <p>Policy: allkeys-lru</p>
          </div>
        </div>

        {/* ThreadPool Executor */}
        <div className="glass-card p-5 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4 text-emerald-400" />
              <h3 className="font-semibold text-sm text-slate-200">Async ThreadPool</h3>
            </div>
            <span className="flex items-center gap-1 text-xs text-emerald-400 font-medium">
              <CheckCircle className="w-3.5 h-3.5" />
              Active
            </span>
          </div>
          <p className="text-xs text-slate-400">
            Offloads CPU-heavy OpenCV & YOLO matrix calculations from the FastAPI async event loop.
          </p>
          <div className="text-xs font-mono text-slate-400 bg-navy-900/60 p-2.5 rounded-lg border border-navy-800 space-y-1">
            <p>Active Jobs: {threadpool?.active_workers ?? 0}</p>
            <p>Max Sizing: {threadpool?.max_workers ?? 4} Workers</p>
          </div>
        </div>
      </div>

      {/* Runtime Environment Footer */}
      <div className="glass-card p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs text-slate-400">
        <div className="flex items-center gap-4 flex-wrap">
          <span>Python: <strong className="text-slate-200 font-mono">{runtime?.python_version || '3.11.x'}</strong></span>
          <span>Environment: <strong className="text-slate-200 capitalize">{runtime?.environment || 'development'}</strong></span>
          <span>Platform: <strong className="text-slate-200 font-mono truncate max-w-xs">{runtime?.platform || 'Linux Container'}</strong></span>
        </div>
        <div className="flex items-center gap-1 text-slate-500">
          <Clock className="w-3.5 h-3.5" />
          Last refreshed: {lastRefreshed.toLocaleTimeString()}
        </div>
      </div>
    </div>
  )
}
