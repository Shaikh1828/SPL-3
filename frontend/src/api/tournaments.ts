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
}
