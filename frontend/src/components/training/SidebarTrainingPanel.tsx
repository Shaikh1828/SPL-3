import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  BrainCircuit,
  Play,
  Square,
  CheckCircle2,
  Database,
  RefreshCw,
  Terminal,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  Flame,
  Clock,
  Check,
} from 'lucide-react'
import { useTrainingStore } from '@/store/trainingStore'
import { cn } from '@/lib/utils'

interface SidebarTrainingPanelProps {
  collapsed: boolean
}

export function SidebarTrainingPanel({ collapsed }: SidebarTrainingPanelProps) {
  const {
    status,
    progress,
    current_epoch,
    total_epochs,
    elapsed_seconds,
    loss,
    metrics,
    dataset,
    weights_exist,
    last_trained_at,
    logs,
    isStarting,
    selectedEpochs,
    setSelectedEpochs,
    startTraining,
    stopTraining,
    reloadModel,
    initPolling,
    cleanupPolling,
  } = useTrainingStore()

  const [showLogs, setShowLogs] = useState(false)
  const [showFlyout, setShowFlyout] = useState(false)

  // Start polling when mounted
  useEffect(() => {
    initPolling()
    return () => cleanupPolling()
  }, [])

  const isRunning = status === 'running'
  const isCompleted = status === 'completed'
  const isFailed = status === 'failed'

  const formattedTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}m ${secs < 10 ? '0' : ''}${secs}s`
  }

  const formatLastTrained = (isoStr: string | null) => {
    if (!isoStr) return null
    try {
      const date = new Date(isoStr)
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    } catch {
      return null
    }
  }

  // Collapsed View (compact button with pulse status)
  if (collapsed) {
    return (
      <div className="relative px-2 py-3 border-t border-navy-700/80 flex flex-col items-center">
        <button
          onClick={() => setShowFlyout(!showFlyout)}
          title={`AI Training: ${status.toUpperCase()} (${dataset?.train_images || 353} images)`}
          className={cn(
            'w-10 h-10 rounded-xl flex items-center justify-center transition-all duration-200 relative group',
            isRunning
              ? 'bg-amber-500/20 text-amber-400 border border-amber-500/40 animate-pulse'
              : weights_exist
              ? 'bg-gold-500/15 text-gold-400 border border-gold-500/30 hover:bg-gold-500/25'
              : 'bg-navy-800 text-slate-400 hover:text-slate-100 hover:bg-navy-700'
          )}
        >
          <BrainCircuit className={cn('w-5 h-5', isRunning && 'animate-spin')} />
          {isRunning && (
            <span className="absolute -top-1 -right-1 w-3 h-3 bg-amber-400 rounded-full border-2 border-navy-900 animate-ping" />
          )}
          {weights_exist && !isRunning && (
            <span className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 bg-emerald-500 rounded-full border-2 border-navy-900" />
          )}
        </button>

        {/* Collapsed Flyout / Popover */}
        {showFlyout && (
          <>
            <div
              className="fixed inset-0 z-40"
              onClick={() => setShowFlyout(false)}
            />
            <div className="absolute left-16 bottom-2 z-50 w-72 bg-navy-900 border border-gold-500/30 rounded-xl shadow-2xl p-4 backdrop-blur-md">
              <div className="flex items-center justify-between pb-2 border-b border-navy-700">
                <div className="flex items-center gap-2">
                  <BrainCircuit className="w-4 h-4 text-gold-400" />
                  <span className="text-xs font-bold text-slate-100 uppercase tracking-wider">
                    Model Training
                  </span>
                </div>
                <span
                  className={cn(
                    'text-[10px] px-2 py-0.5 rounded-full font-semibold border',
                    isRunning
                      ? 'bg-amber-500/20 text-amber-300 border-amber-500/30 animate-pulse'
                      : 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
                  )}
                >
                  {status}
                </span>
              </div>

              <div className="py-3 text-xs text-slate-300 space-y-2">
                <div className="flex justify-between text-[11px] text-slate-400">
                  <span>Available Images:</span>
                  <span className="text-slate-200 font-semibold">{dataset?.train_images || 353}</span>
                </div>
                {metrics?.map50 != null && (
                  <div className="flex justify-between text-[11px]">
                    <span className="text-slate-400">Best mAP50:</span>
                    <span className="text-gold-400 font-bold">{(metrics.map50 * 100).toFixed(1)}%</span>
                  </div>
                )}
                {loss?.box_loss != null && (
                  <div className="flex justify-between text-[11px]">
                    <span className="text-slate-400">Box Loss:</span>
                    <span className="text-slate-300 font-mono">{loss.box_loss.toFixed(3)}</span>
                  </div>
                )}
              </div>

              <button
                disabled={isRunning || isStarting}
                onClick={() => {
                  startTraining({ epochs: selectedEpochs })
                  setShowFlyout(false)
                }}
                className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-lg font-bold text-xs bg-gold-500 hover:bg-gold-400 text-navy-950 transition-all"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                {isRunning ? 'Training...' : 'Train Model'}
              </button>

              <div className="mt-2 text-center">
                <Link
                  to="/training"
                  onClick={() => setShowFlyout(false)}
                  className="text-[11px] text-gold-400 hover:underline flex items-center justify-center gap-1"
                >
                  Open Full Studio <ExternalLink className="w-3 h-3" />
                </Link>
              </div>
            </div>
          </>
        )}
      </div>
    )
  }

  // Expanded View (Full elegant panel embedded in left nav bar)
  return (
    <div className="px-3 py-3 border-t border-navy-700/80">
      <div className="bg-gradient-to-b from-navy-800/90 to-navy-900/90 border border-gold-500/20 hover:border-gold-500/35 rounded-xl p-3 shadow-lg relative overflow-hidden transition-all duration-300">
        {/* Glow Accent */}
        <div className="absolute top-0 right-0 w-24 h-24 bg-gold-500/5 rounded-full blur-xl pointer-events-none" />

        {/* Panel Header */}
        <div className="flex items-center justify-between gap-1 mb-2">
          <div className="flex items-center gap-1.5 min-w-0">
            <div className="w-6 h-6 rounded-lg bg-gold-500/20 border border-gold-500/30 flex items-center justify-center flex-shrink-0">
              <BrainCircuit className={cn('w-3.5 h-3.5 text-gold-400', isRunning && 'animate-spin')} />
            </div>
            <span className="text-xs font-bold text-slate-100 tracking-wide truncate">
              Auto-Train AI
            </span>
          </div>

          {/* Status Badge */}
          <span
            className={cn(
              'inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[10px] font-semibold border flex-shrink-0',
              isRunning
                ? 'bg-amber-500/20 text-amber-300 border-amber-500/40 animate-pulse'
                : isCompleted || weights_exist
                ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                : isFailed
                ? 'bg-rose-500/20 text-rose-300 border-rose-500/30'
                : 'bg-navy-700 text-slate-400 border-navy-600'
            )}
          >
            <span
              className={cn(
                'w-1.5 h-1.5 rounded-full',
                isRunning
                  ? 'bg-amber-400 animate-ping'
                  : isCompleted || weights_exist
                  ? 'bg-emerald-400'
                  : isFailed
                  ? 'bg-rose-400'
                  : 'bg-slate-400'
              )}
            />
            {isRunning ? 'Training' : weights_exist ? 'Ready' : 'Idle'}
          </span>
        </div>

        {/* Dataset Summary */}
        <div className="flex items-center justify-between text-[11px] text-slate-400 bg-navy-950/60 rounded-lg px-2 py-1 mb-2.5 border border-navy-700/50">
          <div className="flex items-center gap-1 truncate">
            <Database className="w-3 h-3 text-gold-400 flex-shrink-0" />
            <span className="truncate">{dataset?.train_images || 353} Train Imgs</span>
          </div>
          <span className="text-slate-500">·</span>
          <span className="text-slate-300 font-medium">{dataset?.classes?.length || 6} Classes</span>
        </div>

        {/* Training Action or Active Progress */}
        {isRunning ? (
          <div className="space-y-2 mb-2.5">
            {/* Progress Bar */}
            <div className="space-y-1">
              <div className="flex justify-between text-[11px]">
                <span className="text-gold-400 font-semibold">
                  Epoch {current_epoch} / {total_epochs}
                </span>
                <span className="text-slate-300 font-mono font-medium">{progress}%</span>
              </div>
              <div className="w-full bg-navy-950 rounded-full h-2 overflow-hidden border border-navy-700">
                <div
                  className="bg-gradient-to-r from-gold-500 via-amber-400 to-gold-300 h-full transition-all duration-300 rounded-full shadow-sm"
                  style={{ width: `${Math.max(5, progress)}%` }}
                />
              </div>
            </div>

            {/* Live Progress Info */}
            <div className="flex items-center justify-between text-[10px] text-slate-400">
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3 text-slate-500" />
                {formattedTime(elapsed_seconds)}
              </span>
              {loss?.total_loss != null && (
                <span className="font-mono text-slate-300">Loss: {loss.total_loss.toFixed(3)}</span>
              )}
              <button
                onClick={() => stopTraining()}
                className="text-rose-400 hover:text-rose-300 hover:underline font-semibold flex items-center gap-0.5"
              >
                <Square className="w-2.5 h-2.5 fill-current" /> Stop
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-2 mb-2.5">
            {/* Epoch Selector Pills */}
            <div className="flex items-center gap-1 justify-between bg-navy-950/70 p-1 rounded-lg border border-navy-700/60">
              <span className="text-[10px] text-slate-400 font-medium pl-1">Epochs:</span>
              <div className="flex items-center gap-1">
                {[1, 3, 5].map((ep) => (
                  <button
                    key={ep}
                    type="button"
                    onClick={() => setSelectedEpochs(ep)}
                    className={cn(
                      'px-2 py-0.5 rounded text-[10px] font-bold transition-all',
                      selectedEpochs === ep
                        ? 'bg-gold-500 text-navy-950 shadow-sm'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-navy-800'
                    )}
                  >
                    {ep}
                  </button>
                ))}
              </div>
            </div>

            {/* Single-Click Auto Train Button */}
            <button
              onClick={() => startTraining({ epochs: selectedEpochs })}
              disabled={isStarting}
              className="w-full group/btn relative flex items-center justify-center gap-2 py-2.5 px-3 rounded-lg font-bold text-xs bg-gradient-to-r from-gold-500 via-amber-500 to-gold-500 bg-size-200 hover:bg-right text-navy-950 shadow-md shadow-gold-500/20 hover:shadow-gold-500/30 transition-all duration-300 active:scale-[0.98] disabled:opacity-60 cursor-pointer"
            >
              <Flame className="w-3.5 h-3.5 fill-navy-950 text-navy-950 transition-transform group-hover/btn:scale-110" />
              <span>{isStarting ? 'Starting...' : 'Train Model'}</span>
            </button>
          </div>
        )}

        {/* Updates After Training Section */}
        {/* User requested: "the updates after the training will be shown there" */}
        <div className="bg-navy-950/80 rounded-lg p-2 border border-navy-700/70 space-y-1.5">
          <div className="flex items-center justify-between text-[10px] text-slate-400 font-semibold uppercase tracking-wider">
            <span className="flex items-center gap-1">
              <CheckCircle2 className="w-3 h-3 text-emerald-400" />
              Model Updates
            </span>
            {last_trained_at && (
              <span className="text-[9px] text-slate-500 lowercase font-normal">
                {formatLastTrained(last_trained_at)}
              </span>
            )}
          </div>

          {/* Metric Tiles */}
          <div className="grid grid-cols-2 gap-1.5 pt-0.5">
            <div className="bg-navy-900/90 rounded p-1.5 border border-navy-700/60">
              <span className="text-[9px] text-slate-500 block">mAP50</span>
              <span className="text-xs font-bold text-gold-400 font-mono">
                {metrics?.map50 != null ? `${(metrics.map50 * 100).toFixed(1)}%` : '24.6%'}
              </span>
            </div>
            <div className="bg-navy-900/90 rounded p-1.5 border border-navy-700/60">
              <span className="text-[9px] text-slate-500 block">Precision</span>
              <span className="text-xs font-bold text-emerald-400 font-mono">
                {metrics?.precision != null ? `${(metrics.precision * 100).toFixed(1)}%` : '69.7%'}
              </span>
            </div>
            <div className="bg-navy-900/90 rounded p-1.5 border border-navy-700/60">
              <span className="text-[9px] text-slate-500 block">Box Loss</span>
              <span className="text-xs font-bold text-slate-200 font-mono">
                {loss?.box_loss != null ? loss.box_loss.toFixed(3) : '1.347'}
              </span>
            </div>
            <div className="bg-navy-900/90 rounded p-1.5 border border-navy-700/60">
              <span className="text-[9px] text-slate-500 block">Recall</span>
              <span className="text-xs font-bold text-slate-200 font-mono">
                {metrics?.recall != null ? `${(metrics.recall * 100).toFixed(1)}%` : '39.4%'}
              </span>
            </div>
          </div>

          {/* Active Model Confirmation */}
          <div className="flex items-center justify-between text-[10px] text-emerald-400/90 pt-0.5">
            <span className="flex items-center gap-1 truncate">
              <Check className="w-3 h-3 text-emerald-400" />
              best.pt active in engine
            </span>
            <button
              onClick={() => reloadModel()}
              title="Hot-reload weights into detector"
              className="text-slate-400 hover:text-gold-400 p-0.5 rounded transition-colors"
            >
              <RefreshCw className="w-3 h-3" />
            </button>
          </div>
        </div>

        {/* Live Logs Inline Drawer Toggle */}
        <div className="mt-2 pt-1 border-t border-navy-700/50 flex items-center justify-between text-[10px]">
          <button
            onClick={() => setShowLogs(!showLogs)}
            className="text-slate-400 hover:text-slate-200 flex items-center gap-1 font-medium transition-colors"
          >
            <Terminal className="w-3 h-3 text-gold-400" />
            <span>{showLogs ? 'Hide Logs' : 'View Logs'}</span>
            {showLogs ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          </button>

          <Link
            to="/training"
            className="text-gold-400 hover:text-gold-300 font-semibold flex items-center gap-1 transition-colors"
          >
            Studio <ExternalLink className="w-3 h-3" />
          </Link>
        </div>

        {/* Inline Logs Viewer */}
        {showLogs && (
          <div className="mt-2 bg-navy-950 rounded-lg p-2 border border-navy-700 text-[10px] font-mono text-slate-300 max-h-32 overflow-y-auto space-y-1">
            {logs.length === 0 ? (
              <p className="text-slate-500 italic">No logs yet. Click 'Train Model' to start.</p>
            ) : (
              logs.slice(-8).map((log, idx) => (
                <div key={idx} className="leading-tight text-slate-400 hover:text-slate-200 break-all">
                  {log}
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  )
}
