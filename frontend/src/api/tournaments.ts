import { apiClient } from './client'
import type { Tournament, TournamentCreate, PaginatedResponse } from '@/types'

export const tournamentsApi = {
  list: (params?: { skip?: number; limit?: number; search?: string }) =>
    apiClient.get<PaginatedResponse<Tournament>>('/tournaments', { params }).then((r) => r.data),

  get: (id: number) =>
    apiClient.get<Tournament>(`/tournaments/${id}`).then((r) => r.data),

  create: (data: TournamentCreate) =>
    apiClient.post<Tournament>('/tournaments', data).then((r) => r.data),
}
