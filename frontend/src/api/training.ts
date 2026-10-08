import { apiClient } from './client'

export interface DatasetInfo {
  name: string
  path: string
  data_yaml: string
  train_images: number
  val_images: number
  test_images: number
  total_images: number
  classes: string[]
  status: string
}

export interface TrainingLossMetrics {
  box_loss?: number | null
  cls_loss?: number | null
  dfl_loss?: number | null
  total_loss?: number | null
}

export interface TrainingEvaluationMetrics {
  precision?: number | null
  recall?: number | null
  map50?: number | null
  map50_95?: number | null
}

export interface TrainingStatusResponse {
  status: 'idle' | 'running' | 'completed' | 'failed' | 'stopped'
  progress: number
  current_epoch: number
  total_epochs: number
  start_time?: string | null
  elapsed_seconds: number
  eta_seconds?: number | null
  loss?: TrainingLossMetrics | null
  metrics?: TrainingEvaluationMetrics | null
  dataset?: DatasetInfo | null
  best_weights?: string | null
  last_checkpoint?: string | null
  weights_exist: boolean
  last_trained_at?: string | null
  logs: string[]
  error?: string | null
}

export interface TrainingHistoryItem {
  epoch: number
  time_seconds?: number | null
  train_box_loss?: number | null
  train_cls_loss?: number | null
  train_dfl_loss?: number | null
  precision?: number | null
  recall?: number | null
  map50?: number | null
  map50_95?: number | null
  val_box_loss?: number | null
  val_cls_loss?: number | null
  val_dfl_loss?: number | null
}

export interface TrainingHistoryResponse {
  total_epochs: number
  items: TrainingHistoryItem[]
  best_map50?: number | null
  best_epoch?: number | null
  weights_file?: string | null
  weights_size_bytes?: number | null
  weights_last_modified?: string | null
}

export interface TrainingStartPayload {
  epochs?: number
  batch_size?: number
  imgsz?: number
  device?: string
  resume?: boolean
}

export const trainingApi = {
  getStatus: () =>
    apiClient.get<TrainingStatusResponse>('/training/status').then((r) => r.data),

  getDataset: () =>
    apiClient.get<DatasetInfo>('/training/dataset').then((r) => r.data),

  getHistory: () =>
    apiClient.get<TrainingHistoryResponse>('/training/history').then((r) => r.data),

  start: (payload?: TrainingStartPayload) =>
    apiClient.post<TrainingStatusResponse>('/training/start', payload || {}).then((r) => r.data),

  stop: () =>
    apiClient.post<TrainingStatusResponse>('/training/stop').then((r) => r.data),

  reloadModel: () =>
    apiClient.post<{ status: string; message: string }>('/training/reload').then((r) => r.data),

  getArtifactUrl: (filename: string) => `/api/training/artifacts/${filename}`,
}
