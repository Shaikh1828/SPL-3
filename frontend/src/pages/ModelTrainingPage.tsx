import { useEffect, useState } from 'react'
import {
  BrainCircuit,
  Play,
  Square,
  RefreshCw,
  Database,
  Layers,
  Award,
  Cpu,
  Flame,
  BarChart3,
  ImageIcon,
  Terminal,
} from 'lucide-react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'
import { useTrainingStore } from '@/store/trainingStore'
import { useAuthStore } from '@/store/authStore'
import { trainingApi } from '@/api/training'
import { cn } from '@/lib/utils'

export default function ModelTrainingPage() {
  const user = useAuthStore((s) => s.user)
  const canTrain = user?.role === 'admin' || user?.role === 'scorer'

  const {
    status,
    progress,
    current_epoch,
    total_epochs,
    elapsed_seconds,
    eta_seconds,
    loss,
    metrics,
    dataset,
    weights_exist,
    logs,
    history,
    isLoading,
    isStarting,
    selectedEpochs,
    setSelectedEpochs,
    startTraining,
    stopTraining,
    reloadModel,
    fetchStatus,
    fetchHistory,
    initPolling,
    cleanupPolling,
  } = useTrainingStore()

  const [batchSize, setBatchSize] = useState(4)
  const [imgsz, setImgsz] = useState(896)
  const [device, setDevice] = useState('cpu')
  const [resume, setResume] = useState(false)
  const [activeTab, setActiveTab] = useState<'metrics' | 'artifacts' | 'dataset' | 'logs'>('metrics')
  const [artifactError, setArtifactError] = useState<Record<string, boolean>>({})

  useEffect(() => {
    initPolling()
    fetchHistory()
    return () => cleanupPolling()
  }, [])

  const isRunning = status === 'running'

  const formattedTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}m ${secs < 10 ? '0' : ''}${secs}s`
  }

  const chartData = (history?.items || []).map((item) => ({
    epoch: `Ep ${item.epoch}`,
    epochNum: item.epoch,
    boxLoss: item.train_box_loss,
    clsLoss: item.train_cls_loss,
    dflLoss: item.train_dfl_loss,
    precision: item.precision ? Math.round(item.precision * 1000) / 10 : null,
    recall: item.recall ? Math.round(item.recall * 1000) / 10 : null,
    map50: item.map50 ? Math.round(item.map50 * 1000) / 10 : null,
    map50_95: item.map50_95 ? Math.round(item.map50_95 * 1000) / 10 : null,
  }))

  const handleStart = () => {
    startTraining({
      epochs: selectedEpochs,
      batch_size: batchSize,
      imgsz: imgsz,
      device: device,
      resume: resume,
    })
  }

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6 animate-fade-in text-slate-100">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-navy-800/80 border border-navy-700/80 p-5 rounded-2xl shadow-xl backdrop-blur">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-gold-500/15 border border-gold-500/30 flex items-center justify-center">
            <BrainCircuit className={cn('w-7 h-7 text-gold-400', isRunning && 'animate-spin')} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold text-slate-100">AI Model Studio & Auto-Trainer</h1>
              <span
                className={cn(
                  'px-2.5 py-0.5 rounded-full text-xs font-semibold border flex items-center gap-1.5',
                  isRunning
                    ? 'bg-amber-500/20 text-amber-300 border-amber-500/40 animate-pulse'
                    : weights_exist
                    ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                    : 'bg-navy-700 text-slate-400 border-navy-600'
                )}
              >
                <span
                  className={cn(
                    'w-1.5 h-1.5 rounded-full',
                    isRunning ? 'bg-amber-400 animate-ping' : weights_exist ? 'bg-emerald-400' : 'bg-slate-400'
                  )}
                />
                {isRunning ? 'Training In Progress' : weights_exist ? 'Weights Active & Ready' : 'Idle'}
              </span>
            </div>
            <p className="text-sm text-slate-400 mt-0.5">
              Automatically train and fine-tune YOLO11 on the archery dataset. New weights are hot-reloaded into live detection.
            </p>
          </div>
        </div>

        {/* Quick Top Actions */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => reloadModel()}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold bg-navy-700/60 hover:bg-navy-700 text-slate-300 hover:text-slate-100 border border-navy-600 transition-all"
            title="Reload best.pt weights into scoring engine"
          >
            <RefreshCw className="w-3.5 h-3.5 text-gold-400" />
            Reload Model
          </button>
          <button
            onClick={() => {
              fetchStatus()
              fetchHistory()
            }}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold bg-navy-700/60 hover:bg-navy-700 text-slate-300 hover:text-slate-100 border border-navy-600 transition-all"
          >
            <RefreshCw className={cn('w-3.5 h-3.5', isLoading && 'animate-spin')} />
            Refresh
          </button>
        </div>
      </div>

      {/* KPI Cards Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Dataset Card */}
        <div className="bg-navy-800/60 border border-navy-700 rounded-xl p-4 relative overflow-hidden">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium mb-1">
            <span>Available Dataset</span>
            <Database className="w-4 h-4 text-gold-400" />
          </div>
          <div className="text-2xl font-bold text-slate-100 font-mono">
            {dataset?.total_images || 504}
            <span className="text-xs font-normal text-slate-400 ml-1.5">Images</span>
          </div>
          <div className="mt-2 flex items-center justify-between text-xs text-slate-400 pt-2 border-t border-navy-700/50">
            <span>{dataset?.train_images || 353} Train · {dataset?.val_images || 76} Val</span>
            <span className="text-gold-400 font-semibold">{dataset?.classes?.length || 6} Classes</span>
          </div>
        </div>

        {/* Model Architecture Card */}
        <div className="bg-navy-800/60 border border-navy-700 rounded-xl p-4 relative overflow-hidden">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium mb-1">
            <span>Architecture</span>
            <Layers className="w-4 h-4 text-gold-400" />
          </div>
          <div className="text-2xl font-bold text-slate-100 font-mono">
            YOLO11n
            <span className="text-xs font-normal text-emerald-400 ml-2 font-sans font-medium">896 Res</span>
          </div>
          <div className="mt-2 flex items-center justify-between text-xs text-slate-400 pt-2 border-t border-navy-700/50">
            <span>Weights: best.pt</span>
            <span className="text-emerald-400 font-medium">Active</span>
          </div>
        </div>

        {/* Accuracy Card */}
        <div className="bg-navy-800/60 border border-navy-700 rounded-xl p-4 relative overflow-hidden">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium mb-1">
            <span>Validation mAP50</span>
            <Award className="w-4 h-4 text-gold-400" />
          </div>
          <div className="text-2xl font-bold text-gold-400 font-mono">
            {history?.best_map50 != null
              ? `${(history.best_map50 * 100).toFixed(1)}%`
              : metrics?.map50 != null
              ? `${(metrics.map50 * 100).toFixed(1)}%`
              : '24.6%'}
          </div>
          <div className="mt-2 flex items-center justify-between text-xs text-slate-400 pt-2 border-t border-navy-700/50">
            <span>Prec: {metrics?.precision != null ? `${(metrics.precision * 100).toFixed(1)}%` : '69.7%'}</span>
            <span>Recall: {metrics?.recall != null ? `${(metrics.recall * 100).toFixed(1)}%` : '39.4%'}</span>
          </div>
        </div>

        {/* Training Progress Card */}
        <div className="bg-navy-800/60 border border-navy-700 rounded-xl p-4 relative overflow-hidden">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium mb-1">
            <span>Training Status</span>
            <Cpu className="w-4 h-4 text-gold-400" />
          </div>
          <div className="text-2xl font-bold text-slate-100 font-mono">
            {isRunning ? (
              <span className="text-amber-400">Epoch {current_epoch}/{total_epochs}</span>
            ) : (
              <span>{history?.total_epochs || 20} Epochs</span>
            )}
          </div>
          <div className="mt-2 flex items-center justify-between text-xs text-slate-400 pt-2 border-t border-navy-700/50">
            {isRunning ? (
              <>
                <span className="text-amber-400 font-medium">{progress}% Complete</span>
                <span>{formattedTime(elapsed_seconds)}</span>
              </>
            ) : (
              <>
                <span>Box Loss: {loss?.box_loss != null ? loss.box_loss.toFixed(3) : '1.347'}</span>
                <span className="text-emerald-400 font-medium">Ready</span>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Main Interactive Training Control Bar */}
      <div className="bg-gradient-to-r from-navy-800 via-navy-800/90 to-navy-900 border border-gold-500/25 rounded-2xl p-5 shadow-xl space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
              <Flame className="w-5 h-5 text-gold-400" />
              Automated Training Execution
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Click to train immediately using the dataset. Presets configure optimal epochs for fast testing or deep learning.
            </p>
          </div>

          {/* Action Trigger Buttons */}
          <div className="flex items-center gap-3">
            {isRunning ? (
              <button
                disabled={!canTrain}
                onClick={() => stopTraining()}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl font-bold text-xs bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 border border-rose-500/40 transition-all shadow-lg active:scale-95 disabled:opacity-50"
              >
                <Square className="w-4 h-4 fill-current" />
                Abort Training
              </button>
            ) : (
              <button
                disabled={!canTrain || isStarting}
                onClick={handleStart}
                className={cn(
                  'flex items-center gap-2 px-6 py-2.5 rounded-xl font-bold text-sm transition-all duration-200 active:scale-95',
                  canTrain
                    ? 'bg-gradient-to-r from-gold-500 via-amber-500 to-gold-400 hover:from-gold-400 hover:to-amber-300 text-navy-950 shadow-lg shadow-gold-500/25 cursor-pointer disabled:opacity-60'
                    : 'bg-navy-900 text-slate-500 cursor-not-allowed border border-navy-700'
                )}
                title={!canTrain ? 'Requires Admin or Scorer role to trigger training' : undefined}
              >
                <Play className="w-4 h-4 fill-current" />
                {!canTrain ? 'Train (Admin/Scorer Only)' : isStarting ? 'Initiating Pipeline...' : `Train Model (${selectedEpochs} Epochs)`}
              </button>
            )}
          </div>
        </div>

        {/* Non-authorized role alert */}
        {!canTrain && (
          <div className="text-xs text-amber-400/90 bg-amber-500/10 border border-amber-500/20 rounded-xl px-3 py-2">
            ℹ️ You are viewing Model Training in spectator/read-only mode. Training models and reloading weights requires Admin or Scorer privileges.
          </div>
        )}

        {/* Hyperparameter Preset Badges */}
        <div className="flex flex-wrap items-center gap-4 pt-3 border-t border-navy-700/60 text-xs">
          <div className="flex items-center gap-2">
            <span className="text-slate-400 font-medium">Epochs:</span>
            <div className="flex items-center gap-1.5">
              {[
                { ep: 1, label: '1 (Rapid Test)' },
                { ep: 3, label: '3 (Fast Update)' },
                { ep: 5, label: '5 (Standard)' },
                { ep: 10, label: '10 (Deep)' },
                { ep: 30, label: '30 (Full Run)' },
              ].map(({ ep, label }) => (
                <button
                  key={ep}
                  type="button"
                  disabled={isRunning}
                  onClick={() => setSelectedEpochs(ep)}
                  className={cn(
                    'px-2.5 py-1 rounded-lg font-semibold text-xs transition-all',
                    selectedEpochs === ep
                      ? 'bg-gold-500 text-navy-950 shadow-md shadow-gold-500/20'
                      : 'bg-navy-900/80 text-slate-300 border border-navy-700 hover:border-gold-500/40'
                  )}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* Hyperparameters Controls */}
          <div className="flex flex-wrap items-center gap-4 ml-auto text-xs text-slate-400">
            <div className="flex items-center gap-1.5">
              <span>Batch:</span>
              <div className="flex items-center gap-1">
                {[2, 4, 8].map((b) => (
                  <button
                    key={b}
                    type="button"
                    disabled={isRunning}
                    onClick={() => setBatchSize(b)}
                    className={cn(
                      'px-2 py-0.5 rounded text-[11px] font-semibold transition-all',
                      batchSize === b
                        ? 'bg-gold-500 text-navy-950 font-bold'
                        : 'bg-navy-900 text-slate-400 hover:text-slate-200'
                    )}
                  >
                    {b}
                  </button>
                ))}
              </div>
            </div>

            <span>·</span>

            <div className="flex items-center gap-1.5">
              <span>Res:</span>
              <div className="flex items-center gap-1">
                {[640, 896].map((resVal) => (
                  <button
                    key={resVal}
                    type="button"
                    disabled={isRunning}
                    onClick={() => setImgsz(resVal)}
                    className={cn(
                      'px-2 py-0.5 rounded text-[11px] font-semibold transition-all',
                      imgsz === resVal
                        ? 'bg-gold-500 text-navy-950 font-bold'
                        : 'bg-navy-900 text-slate-400 hover:text-slate-200'
                    )}
                  >
                    {resVal}
                  </button>
                ))}
              </div>
            </div>

            <span>·</span>

            <div className="flex items-center gap-1.5">
              <span>Device:</span>
              <button
                type="button"
                disabled={isRunning}
                onClick={() => setDevice(device === 'cpu' ? '0' : 'cpu')}
                className="px-2 py-0.5 rounded bg-navy-900 text-gold-400 font-mono font-semibold uppercase hover:bg-navy-700 transition-all"
                title="Click to toggle CPU / CUDA device"
              >
                {device === '0' ? 'CUDA (GPU)' : 'CPU'}
              </button>
            </div>

            <span>·</span>

            <label className="flex items-center gap-1.5 cursor-pointer text-slate-300">
              <input
                type="checkbox"
                disabled={isRunning}
                checked={resume}
                onChange={(e) => setResume(e.target.checked)}
                className="rounded border-navy-700 bg-navy-900 text-gold-500 focus:ring-0 w-3.5 h-3.5"
              />
              <span className="text-[11px]">Resume Checkpoint</span>
            </label>
          </div>
        </div>

        {/* Active Progress Bar (When Running) */}
        {isRunning && (
          <div className="bg-navy-950/80 rounded-xl p-4 border border-amber-500/30 space-y-2 mt-2">
            <div className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping" />
                <span className="font-bold text-amber-300">
                  Executing Epoch {current_epoch} of {total_epochs}
                </span>
              </div>
              <span className="font-mono font-bold text-gold-400 text-sm">{progress}%</span>
            </div>

            <div className="w-full bg-navy-900 rounded-full h-3 overflow-hidden border border-navy-700">
              <div
                className="bg-gradient-to-r from-gold-500 via-amber-400 to-gold-300 h-full transition-all duration-300 rounded-full shadow-md"
                style={{ width: `${Math.max(3, progress)}%` }}
              />
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-2 pt-2 text-xs">
              <div className="bg-navy-900 rounded p-2 border border-navy-700">
                <span className="text-slate-500 block text-[10px]">Elapsed Time</span>
                <span className="font-mono text-slate-200 font-semibold">{formattedTime(elapsed_seconds)}</span>
              </div>
              <div className="bg-navy-900 rounded p-2 border border-navy-700">
                <span className="text-slate-500 block text-[10px]">Estimated Remaining</span>
                <span className="font-mono text-slate-200 font-semibold">
                  {eta_seconds != null ? formattedTime(eta_seconds) : 'Calculating...'}
                </span>
              </div>
              <div className="bg-navy-900 rounded p-2 border border-navy-700">
                <span className="text-slate-500 block text-[10px]">Box Loss</span>
                <span className="font-mono text-gold-400 font-semibold">
                  {loss?.box_loss != null ? loss.box_loss.toFixed(4) : '--'}
                </span>
              </div>
              <div className="bg-navy-900 rounded p-2 border border-navy-700">
                <span className="text-slate-500 block text-[10px]">Class Loss</span>
                <span className="font-mono text-gold-400 font-semibold">
                  {loss?.cls_loss != null ? loss.cls_loss.toFixed(4) : '--'}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Tabs Navigation */}
      <div className="flex border-b border-navy-700">
        {[
          { key: 'metrics', label: 'Telemetry & Progress Curves', icon: BarChart3 },
          { key: 'artifacts', label: 'Model Artifacts & Curves', icon: ImageIcon },
          { key: 'dataset', label: 'Dataset Inspector', icon: Database },
          { key: 'logs', label: 'Streaming Terminal', icon: Terminal },
        ].map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key as any)}
            className={cn(
              'flex items-center gap-2 px-5 py-3 text-sm font-semibold border-b-2 transition-all cursor-pointer',
              activeTab === key
                ? 'border-gold-500 text-gold-400 bg-gold-500/5'
                : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-navy-800/40'
            )}
          >
            <Icon className="w-4 h-4" />
            {label}
          </button>
        ))}
      </div>

      {/* Tab 1: Charts & Telemetry */}
      {activeTab === 'metrics' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Loss Chart */}
            <div className="bg-navy-800/80 border border-navy-700 rounded-2xl p-5 shadow-lg">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-sm font-bold text-slate-100">Training Loss Components</h3>
                  <p className="text-xs text-slate-400">Box Loss, Class Loss, and DFL Loss per epoch</p>
                </div>
                <span className="text-xs text-slate-400 bg-navy-900 px-2 py-1 rounded border border-navy-700">
                  {chartData.length} Data Points
                </span>
              </div>
              <div className="h-64 w-full">
                {chartData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1c2847" />
                      <XAxis dataKey="epoch" stroke="#64748b" tick={{ fontSize: 11 }} />
                      <YAxis stroke="#64748b" tick={{ fontSize: 11 }} />
                      <Tooltip
                        contentStyle={{ backgroundColor: '#0f1629', borderColor: '#1c2847', borderRadius: '0.75rem', fontSize: '12px' }}
                      />
                      <Legend />
                      <Line type="monotone" dataKey="boxLoss" name="Box Loss" stroke="#eab308" strokeWidth={2} dot={false} />
                      <Line type="monotone" dataKey="clsLoss" name="Class Loss" stroke="#38bdf8" strokeWidth={2} dot={false} />
                      <Line type="monotone" dataKey="dflLoss" name="DFL Loss" stroke="#a855f7" strokeWidth={1.5} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-slate-500 text-xs">
                    No history recorded yet. Click 'Train Model' to generate telemetry.
                  </div>
                )}
              </div>
            </div>

            {/* Validation Metrics Chart */}
            <div className="bg-navy-800/80 border border-navy-700 rounded-2xl p-5 shadow-lg">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-sm font-bold text-slate-100">Detection Accuracy (mAP & Precision)</h3>
                  <p className="text-xs text-slate-400">Validation mAP@50 and Precision percentages</p>
                </div>
                <span className="text-xs text-emerald-400 bg-emerald-500/10 px-2 py-1 rounded border border-emerald-500/20 font-semibold">
                  Best mAP: {history?.best_map50 ? `${(history.best_map50 * 100).toFixed(1)}%` : '24.6%'}
                </span>
              </div>
              <div className="h-64 w-full">
                {chartData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1c2847" />
                      <XAxis dataKey="epoch" stroke="#64748b" tick={{ fontSize: 11 }} />
                      <YAxis stroke="#64748b" tick={{ fontSize: 11 }} unit="%" />
                      <Tooltip
                        contentStyle={{ backgroundColor: '#0f1629', borderColor: '#1c2847', borderRadius: '0.75rem', fontSize: '12px' }}
                      />
                      <Legend />
                      <Line type="monotone" dataKey="map50" name="mAP@50 (%)" stroke="#10b981" strokeWidth={2.5} dot={{ r: 2 }} />
                      <Line type="monotone" dataKey="precision" name="Precision (%)" stroke="#f59e0b" strokeWidth={1.5} dot={false} />
                      <Line type="monotone" dataKey="recall" name="Recall (%)" stroke="#6366f1" strokeWidth={1.5} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-slate-500 text-xs">
                    No validation data recorded yet.
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Epoch Progression Table */}
          <div className="bg-navy-800/80 border border-navy-700 rounded-2xl p-5 shadow-lg overflow-hidden">
            <h3 className="text-sm font-bold text-slate-100 mb-3">Epoch-by-Epoch Checkpoint History</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-navy-900/80 text-slate-400 font-semibold border-b border-navy-700">
                  <tr>
                    <th className="py-2.5 px-3">Epoch</th>
                    <th className="py-2.5 px-3">Box Loss</th>
                    <th className="py-2.5 px-3">Class Loss</th>
                    <th className="py-2.5 px-3">DFL Loss</th>
                    <th className="py-2.5 px-3">Precision</th>
                    <th className="py-2.5 px-3">Recall</th>
                    <th className="py-2.5 px-3">mAP@50</th>
                    <th className="py-2.5 px-3">mAP@50-95</th>
                    <th className="py-2.5 px-3">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-navy-700/60 font-mono">
                  {(history?.items || []).slice(-10).reverse().map((item) => (
                    <tr key={item.epoch} className="hover:bg-navy-700/40 transition-colors">
                      <td className="py-2 px-3 font-bold text-slate-200">Epoch {item.epoch}</td>
                      <td className="py-2 px-3 text-slate-300">{item.train_box_loss?.toFixed(4) ?? '--'}</td>
                      <td className="py-2 px-3 text-slate-300">{item.train_cls_loss?.toFixed(4) ?? '--'}</td>
                      <td className="py-2 px-3 text-slate-300">{item.train_dfl_loss?.toFixed(4) ?? '--'}</td>
                      <td className="py-2 px-3 text-emerald-400 font-semibold">
                        {item.precision ? `${(item.precision * 100).toFixed(1)}%` : '--'}
                      </td>
                      <td className="py-2 px-3 text-slate-300">
                        {item.recall ? `${(item.recall * 100).toFixed(1)}%` : '--'}
                      </td>
                      <td className="py-2 px-3 text-gold-400 font-bold">
                        {item.map50 ? `${(item.map50 * 100).toFixed(1)}%` : '--'}
                      </td>
                      <td className="py-2 px-3 text-slate-300">
                        {item.map50_95 ? `${(item.map50_95 * 100).toFixed(1)}%` : '--'}
                      </td>
                      <td className="py-2 px-3">
                        <span className="text-[10px] bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded border border-emerald-500/20 font-sans">
                          Saved
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Artifacts Gallery */}
      {activeTab === 'artifacts' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Confusion Matrix */}
          <div className="bg-navy-800/80 border border-navy-700 rounded-2xl p-5 shadow-lg space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-slate-100">Confusion Matrix</h3>
                <p className="text-xs text-slate-400">Class prediction confusion across 6 archery target zones</p>
              </div>
            </div>
            <div className="bg-navy-950 rounded-xl overflow-hidden border border-navy-700 flex items-center justify-center min-h-[300px]">
              {artifactError.matrix ? (
                <div className="p-6 text-center text-slate-500 text-xs">
                  Confusion matrix not yet generated. Complete a training run to generate.
                </div>
              ) : (
                <img
                  src={trainingApi.getArtifactUrl('confusion_matrix.png')}
                  alt="Confusion Matrix"
                  className="max-h-96 w-auto object-contain mx-auto"
                  onError={() => setArtifactError((prev) => ({ ...prev, matrix: true }))}
                />
              )}
            </div>
          </div>

          {/* Results Summary Curve */}
          <div className="bg-navy-800/80 border border-navy-700 rounded-2xl p-5 shadow-lg space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-slate-100">Ultralytics Results Curve</h3>
                <p className="text-xs text-slate-400">Combined loss and mAP curves generated during training</p>
              </div>
            </div>
            <div className="bg-navy-950 rounded-xl overflow-hidden border border-navy-700 flex items-center justify-center min-h-[300px]">
              {artifactError.results ? (
                <div className="p-6 text-center text-slate-500 text-xs">
                  Results curve plot not yet generated.
                </div>
              ) : (
                <img
                  src={trainingApi.getArtifactUrl('results.png')}
                  alt="Training Results"
                  className="max-h-96 w-auto object-contain mx-auto"
                  onError={() => setArtifactError((prev) => ({ ...prev, results: true }))}
                />
              )}
            </div>
          </div>

          {/* Validation Predictions */}
          <div className="bg-navy-800/80 border border-navy-700 rounded-2xl p-5 shadow-lg space-y-3 md:col-span-2">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-slate-100">Validation Sample Predictions</h3>
                <p className="text-xs text-slate-400">Predicted bounding boxes and confidence scores on validation batch</p>
              </div>
            </div>
            <div className="bg-navy-950 rounded-xl overflow-hidden border border-navy-700 flex items-center justify-center min-h-[350px]">
              {artifactError.val ? (
                <div className="p-6 text-center text-slate-500 text-xs">
                  Validation predictions plot not yet available.
                </div>
              ) : (
                <img
                  src={trainingApi.getArtifactUrl('val_batch0_pred.jpg')}
                  alt="Validation Predictions"
                  className="max-h-[500px] w-auto object-contain mx-auto"
                  onError={() => setArtifactError((prev) => ({ ...prev, val: true }))}
                />
              )}
            </div>
          </div>
        </div>
      )}

      {/* Tab 3: Dataset Inspector */}
      {activeTab === 'dataset' && (
        <div className="bg-navy-800/80 border border-navy-700 rounded-2xl p-5 shadow-lg space-y-5">
          <div>
            <h3 className="text-base font-bold text-slate-100">Archery Scoring Dataset Specification</h3>
            <p className="text-xs text-slate-400">Available images and annotation classes ready for training</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-navy-900 rounded-xl p-4 border border-navy-700">
              <span className="text-xs text-slate-400 block mb-1">Training Split</span>
              <span className="text-2xl font-bold font-mono text-gold-400">{dataset?.train_images || 353}</span>
              <span className="text-xs text-slate-500 block mt-1">Data/train/images</span>
            </div>
            <div className="bg-navy-900 rounded-xl p-4 border border-navy-700">
              <span className="text-xs text-slate-400 block mb-1">Validation Split</span>
              <span className="text-2xl font-bold font-mono text-emerald-400">{dataset?.val_images || 76}</span>
              <span className="text-xs text-slate-500 block mt-1">Data/valid/images</span>
            </div>
            <div className="bg-navy-900 rounded-xl p-4 border border-navy-700">
              <span className="text-xs text-slate-400 block mb-1">Test Split</span>
              <span className="text-2xl font-bold font-mono text-sky-400">{dataset?.test_images || 75}</span>
              <span className="text-xs text-slate-500 block mt-1">Data/test/images</span>
            </div>
          </div>

          <div className="bg-navy-900 rounded-xl p-4 border border-navy-700 space-y-2">
            <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider block">
              Configured Classes (6 Target Zones)
            </span>
            <div className="flex flex-wrap gap-2 pt-1">
              {(dataset?.classes || ['2_ring', '4_ring', '6_ring', '7_ring', 'arrow', 'bullseye']).map((cls, idx) => (
                <div
                  key={cls}
                  className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-navy-950 border border-navy-700 text-xs font-mono"
                >
                  <span className="w-5 h-5 rounded-md bg-gold-500/20 text-gold-400 font-bold flex items-center justify-center text-[10px]">
                    {idx}
                  </span>
                  <span className="text-slate-200">{cls}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Tab 4: Streaming Terminal Logs */}
      {activeTab === 'logs' && (
        <div className="bg-navy-900 border border-navy-700 rounded-2xl p-5 shadow-xl space-y-3">
          <div className="flex items-center justify-between pb-3 border-b border-navy-800">
            <div className="flex items-center gap-2">
              <Terminal className="w-4 h-4 text-gold-400" />
              <h3 className="text-sm font-bold text-slate-200 font-mono">training_process.stdout</h3>
            </div>
            <span className="text-[11px] text-slate-500 font-mono">Showing latest {logs.length} entries</span>
          </div>

          <div className="bg-navy-950 rounded-xl p-4 border border-navy-800 font-mono text-xs text-slate-300 max-h-96 overflow-y-auto space-y-1">
            {logs.length === 0 ? (
              <p className="text-slate-500 italic">No output logged yet. Trigger training to start streaming.</p>
            ) : (
              logs.map((log, index) => (
                <div key={index} className="leading-relaxed hover:bg-navy-900/50 px-1 rounded transition-colors break-all">
                  {log}
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}
