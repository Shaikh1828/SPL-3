import { apiClient } from './client'
import type { HealthStatus, DetailedHealth } from '@/types'

export const healthApi = {
  basic: () => apiClient.get<HealthStatus>('/health').then((r) => r.data),
  detailed: () => apiClient.get<DetailedHealth>('/health/detailed').then((r) => r.data),
}

export const reportsApi = {
  generate: (sessionId: number, format: 'pdf' | 'csv' | 'json' = 'pdf') =>
    apiClient.post(`/sessions/${sessionId}/reports`, null, {
      params: { format },
      responseType: format === 'pdf' || format === 'csv' ? 'blob' : 'json',
    }).then((r) => r.data),

  get: (sessionId: number, reportType: string) =>
    apiClient.get(`/sessions/${sessionId}/reports/${reportType}`).then((r) => r.data),
}
