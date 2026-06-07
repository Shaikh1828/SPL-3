import { apiClient } from './client'
import type { Score, ScoreCreate, ScoreValidate, PaginatedResponse } from '@/types'

export const scoresApi = {
  record: (sessionId: number, data: ScoreCreate) =>
    apiClient.post<Score>(`/sessions/${sessionId}/scores`, data).then((r) => r.data),

  list: (sessionId: number, params?: { round_number?: number; skip?: number; limit?: number }) =>
    apiClient
      .get<PaginatedResponse<Score>>(`/sessions/${sessionId}/scores`, { params })
      .then((r) => r.data),

  get: (scoreId: number) =>
    apiClient.get<Score>(`/scores/${scoreId}`).then((r) => r.data),

  validate: (scoreId: number, data: ScoreValidate) =>
    apiClient.post<Score>(`/scores/${scoreId}/validate`, data).then((r) => r.data),
}
