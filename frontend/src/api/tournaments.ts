import { apiClient } from './client'
import type { Tournament, TournamentCreate, PaginatedResponse, LeaderboardEntry } from '@/types'

export const tournamentsApi = {
  list: (params?: { skip?: number; limit?: number; search?: string; status?: string }) =>
    apiClient.get<PaginatedResponse<Tournament>>('/tournaments', { params }).then((r) => r.data),

  get: (id: number) =>
    apiClient.get<Tournament>(`/tournaments/${id}`).then((r) => r.data),

  create: (data: TournamentCreate) =>
    apiClient.post<Tournament>('/tournaments', data).then((r) => r.data),

  update: (id: number, data: TournamentCreate) =>
    apiClient.put<Tournament>(`/tournaments/${id}`, data).then((r) => r.data),

  delete: (id: number) =>
    apiClient.delete<{ message: string; id: number }>(`/tournaments/${id}`).then((r) => r.data),

  getLeaderboard: (id: number) =>
    apiClient.get<LeaderboardEntry[]>(`/tournaments/${id}/leaderboard`).then((r) => r.data),

  getStageProgression: (id: number) =>
    apiClient.get(`/tournaments/${id}/stage-progression`).then((r) => r.data),

  advanceStage: (id: number, data: { source_session_id: number; target_session_id: number; top_qualifiers_count?: number; clear_target?: boolean }) =>
    apiClient.post(`/tournaments/${id}/advance-stage`, data).then((r) => r.data),
}
