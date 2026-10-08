import { create } from 'zustand'
import {
  trainingApi,
  type TrainingStatusResponse,
  type TrainingHistoryResponse,
  type DatasetInfo,
  type TrainingStartPayload,
} from '@/api/training'
import toast from 'react-hot-toast'

interface TrainingStoreState {
  status: 'idle' | 'running' | 'completed' | 'failed' | 'stopped'
  progress: number
  current_epoch: number
  total_epochs: number
  start_time: string | null
  elapsed_seconds: number
  eta_seconds: number | null
  loss: {
    box_loss?: number | null
    cls_loss?: number | null
    dfl_loss?: number | null
    total_loss?: number | null
  }
  metrics: {
    precision?: number | null
    recall?: number | null
    map50?: number | null
    map50_95?: number | null
  }
  dataset: DatasetInfo | null
  best_weights: string | null
  last_checkpoint: string | null
  weights_exist: boolean
  last_trained_at: string | null
  logs: string[]
  error: string | null
  history: TrainingHistoryResponse | null
  isLoading: boolean
  isStarting: boolean
  selectedEpochs: number
  pollIntervalId: any

  // Actions
  fetchStatus: () => Promise<TrainingStatusResponse | null>
  fetchHistory: () => Promise<TrainingHistoryResponse | null>
  startTraining: (payload?: TrainingStartPayload) => Promise<boolean>
  stopTraining: () => Promise<boolean>
  reloadModel: () => Promise<boolean>
  setSelectedEpochs: (epochs: number) => void
  initPolling: () => void
  cleanupPolling: () => void
}

export const useTrainingStore = create<TrainingStoreState>()((set, get) => ({
  status: 'idle',
  progress: 0,
  current_epoch: 0,
  total_epochs: 0,
  start_time: null,
  elapsed_seconds: 0,
  eta_seconds: null,
  loss: {},
  metrics: {},
  dataset: null,
  best_weights: null,
  last_checkpoint: null,
  weights_exist: false,
  last_trained_at: null,
  logs: [],
  error: null,
  history: null,
  isLoading: false,
  isStarting: false,
  selectedEpochs: 3,
  pollIntervalId: null,

  fetchStatus: async () => {
    try {
      const data = await trainingApi.getStatus()
      set({
        status: data.status,
        progress: data.progress,
        current_epoch: data.current_epoch,
        total_epochs: data.total_epochs,
        start_time: data.start_time || null,
        elapsed_seconds: data.elapsed_seconds,
        eta_seconds: data.eta_seconds ?? null,
        loss: data.loss || {},
        metrics: data.metrics || {},
        dataset: data.dataset || null,
        best_weights: data.best_weights || null,
        last_checkpoint: data.last_checkpoint || null,
        weights_exist: data.weights_exist,
        last_trained_at: data.last_trained_at || null,
        logs: data.logs || [],
        error: data.error || null,
      })
      return data
    } catch (err: any) {
      console.error('Failed to fetch training status', err)
      return null
    }
  },

  fetchHistory: async () => {
    try {
      set({ isLoading: true })
      const hist = await trainingApi.getHistory()
      set({ history: hist, isLoading: false })
      return hist
    } catch (err) {
      console.error('Failed to fetch training history', err)
      set({ isLoading: false })
      return null
    }
  },

  startTraining: async (customPayload) => {
    const { selectedEpochs, fetchStatus, fetchHistory } = get()
    const payload: TrainingStartPayload = {
      epochs: customPayload?.epochs ?? selectedEpochs,
      batch_size: customPayload?.batch_size ?? 4,
      imgsz: customPayload?.imgsz ?? 896,
      device: customPayload?.device ?? 'cpu',
      resume: customPayload?.resume ?? false,
    }

    try {
      set({ isStarting: true })
      toast.loading(`Initiating model training (${payload.epochs} epochs)...`, { id: 'train-toast' })
      const res = await trainingApi.start(payload)
      set({
        isStarting: false,
        status: res.status,
        total_epochs: res.total_epochs,
        current_epoch: res.current_epoch,
        progress: res.progress,
      })
      toast.success('Training started! Monitoring progress...', { id: 'train-toast' })
      await fetchStatus()
      // Refresh history as well
      fetchHistory()
      return true
    } catch (err: any) {
      set({ isStarting: false })
      const msg = err.response?.data?.detail || err.message || 'Failed to start training'
      toast.error(msg, { id: 'train-toast' })
      return false
    }
  },

  stopTraining: async () => {
    try {
      toast.loading('Stopping training...', { id: 'train-stop' })
      const res = await trainingApi.stop()
      set({ status: res.status })
      toast.success('Training stopped.', { id: 'train-stop' })
      return true
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Failed to stop training'
      toast.error(msg, { id: 'train-stop' })
      return false
    }
  },

  reloadModel: async () => {
    try {
      toast.loading('Hot-reloading model into engine...', { id: 'reload-toast' })
      const res = await trainingApi.reloadModel()
      toast.success(res.message || 'Model successfully reloaded!', { id: 'reload-toast' })
      get().fetchStatus()
      return true
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Failed to reload model'
      toast.error(msg, { id: 'reload-toast' })
      return false
    }
  },

  setSelectedEpochs: (epochs) => set({ selectedEpochs: epochs }),

  initPolling: () => {
    const existing = get().pollIntervalId
    if (existing) clearInterval(existing)

    // Immediate initial fetch
    get().fetchStatus()
    get().fetchHistory()

    const intervalId = setInterval(() => {
      const currentStatus = get().status
      // Poll every 1.5s if running, otherwise every 10s
      get().fetchStatus().then((res) => {
        // If it was running and just completed, fetch updated history and notify
        if (currentStatus === 'running' && res?.status === 'completed') {
          toast.success('🎉 Training completed! Model updated.', { duration: 6000 })
          get().fetchHistory()
        }
      })
    }, 2000)

    set({ pollIntervalId: intervalId })
  },

  cleanupPolling: () => {
    const existing = get().pollIntervalId
    if (existing) {
      clearInterval(existing)
      set({ pollIntervalId: null })
    }
  },
}))
