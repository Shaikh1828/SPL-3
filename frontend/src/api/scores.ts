import { apiClient } from './client'
import type { Score, ScoreCreate, ScoreValidate } from '@/types'

export const scoresApi = {
  record: (sessionId: number, data: ScoreCreate) =>
    apiClient.post<Score>(`/sessions/${sessionId}/scores`, data).then((r) => r.data),

  upload: (sessionId: number, formData: FormData) =>
    apiClient
      .post<Score>(`/sessions/${sessionId}/scores/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })
      .then((r) => r.data),

  batchDirectory: (sessionId: number, data: { directory_path: string; session_archer_id: number; round: number }) =>
    apiClient
      .post<any[]>(`/sessions/${sessionId}/scores/batch-directory`, data)
      .then((r) => r.data),

  list: (sessionId: number, params?: { round_number?: number; skip?: number; limit?: number }) =>
    apiClient
      .get<Score[]>(`/sessions/${sessionId}/scores`, { params })
      .then((r) => r.data),

  get: (scoreId: number) =>
    apiClient.get<Score>(`/scores/${scoreId}`).then((r) => r.data),

  validate: (scoreId: number, data: ScoreValidate) =>
    apiClient.post<Score>(`/scores/${scoreId}/validate`, data).then((r) => r.data),

  getRawImageUrl: (scoreId: number) => `/scores/${scoreId}/image`,

  getAnnotatedImageUrl: (scoreId: number) => `/scores/${scoreId}/image-annotated`,

  override: (scoreId: number, data: { zone: number; points: number; reason?: string }) =>
    apiClient.put<Score>(`/scores/${scoreId}/override`, data).then((r) => r.data),

  delete: (scoreId: number) =>
    apiClient.delete<{ message: string; score_id: number }>(`/scores/${scoreId}`).then((r) => r.data),

  recent: (limit: number = 15) =>
    apiClient.get<import('@/types').RecentScoreItem[]>('/scores/recent', { params: { limit } }).then((r) => r.data),

  aiScoreRound: (sessionId: number, data: { round: number; simulated?: boolean }) =>
    apiClient
      .post<import('@/types').AIScoreRoundResponse>(`/sessions/${sessionId}/ai-score-round`, data)
      .then((r) => r.data),

  batchConfirmRound: (sessionId: number, data: import('@/types').BatchConfirmRoundRequest) =>
    apiClient
      .post<import('@/types').BatchConfirmRoundResponse>(`/sessions/${sessionId}/scores/batch-confirm-round`, data)
      .then((r) => r.data),

  gallery: (params?: import('@/types').ScoreGalleryFilterParams) =>
    apiClient
      .get<import('@/types').ScoreGalleryResponse>('/scores/gallery', { params })
      .then((r) => r.data),

  captureLaneScore: (sessionId: number, laneNumber: number, round: number = 1) =>
    apiClient
      .post<Score>(`/sessions/${sessionId}/lanes/${laneNumber}/capture-score`, null, { params: { round } })
      .then((r) => r.data),
}

