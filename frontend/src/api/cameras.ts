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

  update: (id: number, data: { name?: string; camera_type?: string; url?: string }) =>
    apiClient
      .put<Camera>(`/cameras/${id}`, data)
      .then((r) => r.data),

  quickSetupObs: (sessionId: number) =>
    apiClient
      .post<{ success: boolean; message: string; lanes_configured: number }>(
        `/sessions/${sessionId}/quick-setup-obs`
      )
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

  testStream: (data: { url: string; camera_type: string }) =>
    apiClient
      .post<import('@/types').CameraTestResponse>('/cameras/test-stream', data)
      .then((r) => r.data),

  testCamera: (cameraId: number) =>
    apiClient
      .get<import('@/types').CameraTestResponse>(`/cameras/${cameraId}/test`)
      .then((r) => r.data),

  discover: () =>
    apiClient
      .get<import('@/types').CameraDiscoveryItem[]>('/cameras/discover')
      .then((r) => r.data),

  pushFrame: (cameraId: number, imageBase64: string) =>
    apiClient
      .post<{ success: boolean }>(`/cameras/${cameraId}/push-frame`, { image_base64: imageBase64 })
      .then((r) => r.data),

  pushLaneFrame: (sessionId: number, lane: number, imageBase64: string) =>
    apiClient
      .post<{ success: boolean }>(`/sessions/${sessionId}/lanes/${lane}/push-frame`, { image_base64: imageBase64 })
      .then((r) => r.data),
}
