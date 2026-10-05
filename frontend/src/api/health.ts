import { apiClient } from './client'
import type { HealthStatus, DetailedHealth, SystemMetrics } from '@/types'

export const healthApi = {
  basic: () => apiClient.get<HealthStatus>('/health').then((r) => r.data),
  detailed: () => apiClient.get<DetailedHealth>('/health/detailed').then((r) => r.data),
  systemMetrics: () => apiClient.get<SystemMetrics>('/health/system').then((r) => r.data),
}

export { reportsApi } from './reports'

