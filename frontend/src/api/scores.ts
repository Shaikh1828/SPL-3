import { apiClient } from './client'
import type { Score, ScoreCreate, ScoreValidate, PaginatedResponse } from '@/types'

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
      .get<PaginatedResponse<Score>>(`/sessions/${sessionId}/scores`, { params })
      .then((r) => r.data),

  get: (scoreId: number) =>
    apiClient.get<Score>(`/scores/${scoreId}`).then((r) => r.data),

  validate: (scoreId: number, data: ScoreValidate) =>
    apiClient.post<Score>(`/scores/${scoreId}/validate`, data).then((r) => r.data),
}
