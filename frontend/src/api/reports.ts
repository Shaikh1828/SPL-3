import { apiClient } from './client'
import type {
  TournamentAnalyticsResponse,
  ArcherLongitudinalAnalyticsResponse,
  ArcherDirectoryItem,
} from '@/types'

export const reportsApi = {
  // Session-level report export (pdf, csv, json)
  generateSessionReport: (sessionId: number, format: 'pdf' | 'csv' | 'json' = 'pdf') =>
    apiClient.post(`/sessions/${sessionId}/reports`, null, {
      params: { format },
      responseType: format === 'pdf' || format === 'csv' ? 'blob' : 'json',
    }).then((r) => r.data),

  // Tournament-wide report export across all sessions (pdf, csv, json)
  generateTournamentReport: (tournamentId: number, format: 'pdf' | 'csv' | 'json' = 'pdf') =>
    apiClient.post(`/tournaments/${tournamentId}/reports`, null, {
      params: { format },
      responseType: format === 'pdf' || format === 'csv' ? 'blob' : 'json',
    }).then((r) => r.data),

  // Real-time statistical analytics (score distribution, progression, lanes, AI telemetry)
  getAnalytics: (params?: { tournamentId?: number; sessionId?: number }) =>
    apiClient.get<TournamentAnalyticsResponse>('/reports/analytics', {
      params: {
        tournament_id: params?.tournamentId,
        session_id: params?.sessionId,
      },
    }).then((r) => r.data),

  // Directory of distinct archers
  listArchersDirectory: () =>
    apiClient.get<ArcherDirectoryItem[]>('/reports/archers/directory').then((r) => r.data),

  // Longitudinal multi-tournament analytics for an archer
  getArcherLongitudinalAnalytics: (archerId: number, archerName?: string) =>
    apiClient.get<ArcherLongitudinalAnalyticsResponse>(`/reports/archers/${archerId}/analytics`, {
      params: { archer_name: archerName },
    }).then((r) => r.data),

  // Backward-compatibility aliases
  generate: (sessionId: number, format: 'pdf' | 'csv' | 'json' = 'pdf') =>
    apiClient.post(`/sessions/${sessionId}/reports`, null, {
      params: { format },
      responseType: format === 'pdf' || format === 'csv' ? 'blob' : 'json',
    }).then((r) => r.data),

  get: (sessionId: number, reportType: string) =>
    apiClient.get(`/sessions/${sessionId}/reports/${reportType}`).then((r) => r.data),
}
