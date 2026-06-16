import { apiClient } from './client'
import type { Camera, CameraLaneAssignment, AssignCameraRequest } from '@/types'

export const camerasApi = {
  listForSession: (sessionId: number) =>
    apiClient
      .get<Camera[]>(`/sessions/${sessionId}/cameras`)
      .then((r) => r.data),

  listGlobal: () =>
    apiClient
      .get<Camera[]>('/cameras')
      .then((r) => r.data),

  create: (data: { name: string; camera_type: string; url: string }) =>
    apiClient
      .post<Camera>('/cameras', data)
      .then((r) => r.data),

  delete: (id: number) =>
    apiClient
      .delete(`/cameras/${id}`)
      .then((r) => r.data),

  unassign: (sessionId: number, cameraId: number) =>
    apiClient
      .delete(`/sessions/${sessionId}/cameras/${cameraId}`)
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

  listAssignments: (sessionId: number) =>
    apiClient
      .get<CameraLaneAssignment[]>(`/sessions/${sessionId}/assignments`)
      .then((r) => r.data),
}
