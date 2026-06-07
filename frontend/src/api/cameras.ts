import { apiClient } from './client'
import type { Camera, CameraLaneAssignment, AssignCameraRequest, PaginatedResponse } from '@/types'

export const camerasApi = {
  listForSession: (sessionId: number) =>
    apiClient
      .get<PaginatedResponse<Camera>>(`/sessions/${sessionId}/cameras`)
      .then((r) => r.data),

  connect: (sessionId: number, cameraId: number) =>
    apiClient
      .post<Camera>(`/sessions/${sessionId}/cameras/${cameraId}/connect`)
      .then((r) => r.data),

  disconnect: (sessionId: number, cameraId: number) =>
    apiClient
      .post<Camera>(`/sessions/${sessionId}/cameras/${cameraId}/disconnect`)
      .then((r) => r.data),

  reconnect: (cameraId: number) =>
    apiClient.post(`/cameras/${cameraId}/reconnect`).then((r) => r.data),

  assign: (sessionId: number, data: AssignCameraRequest) =>
    apiClient
      .post<CameraLaneAssignment>(`/sessions/${sessionId}/cameras/assign`, data)
      .then((r) => r.data),
}
