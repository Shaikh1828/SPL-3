import { apiClient } from './client'
import type {
  Session, SessionCreate, SessionArcher, SessionArcherCreate,
  PaginatedResponse, LeaderboardEntry
} from '@/types'

export const sessionsApi = {
  listForTournament: (tournamentId: number, params?: { skip?: number; limit?: number; status?: string }) =>
    apiClient
      .get<PaginatedResponse<Session>>(`/tournaments/${tournamentId}/sessions`, { params })
      .then((r) => r.data),

  create: (tournamentId: number, data: SessionCreate) =>
    apiClient.post<Session>(`/tournaments/${tournamentId}/sessions`, data).then((r) => r.data),

  get: (sessionId: number) =>
    apiClient.get<Session>(`/sessions/${sessionId}`).then((r) => r.data),

  updateStatus: (sessionId: number, status: string) =>
    apiClient.patch<Session>(`/sessions/${sessionId}`, { status }).then((r) => r.data),

  registerArcher: (sessionId: number, data: SessionArcherCreate) =>
    apiClient.post<SessionArcher>(`/sessions/${sessionId}/archers`, data).then((r) => r.data),

  listArchers: (sessionId: number) =>
    apiClient.get<SessionArcher[]>(`/sessions/${sessionId}/archers`).then((r) => r.data),

  removeArcher: (sessionId: number, sessionArcherId: number) =>
    apiClient.delete(`/sessions/${sessionId}/archers/${sessionArcherId}`).then((r) => r.data),

  getLeaderboard: (sessionId: number, limit = 100) =>
    apiClient
      .get<LeaderboardEntry[]>(`/sessions/${sessionId}/leaderboard`, { params: { limit } })
      .then((r) => r.data),
}
