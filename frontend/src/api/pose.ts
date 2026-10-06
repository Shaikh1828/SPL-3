import { apiClient } from './client'
import type { SampleVideoItem, PoseAnalysisResponse } from '@/types'

export const poseApi = {
  getSampleVideos: () =>
    apiClient
      .get<{ videos: SampleVideoItem[]; total: number }>('/pose/sample-videos')
      .then((r) => r.data),

  getSampleVideoDetails: (videoId: string) =>
    apiClient
      .get<SampleVideoItem>(`/pose/sample-videos/${videoId}`)
      .then((r) => r.data),

  analyzeSampleVideo: (videoId: string) =>
    apiClient
      .post<PoseAnalysisResponse>(`/pose/sample-videos/${videoId}/analyze`)
      .then((r) => r.data),

  analyzeUploadedVideo: (formData: FormData) =>
    apiClient
      .post<PoseAnalysisResponse>('/pose/analyze-video', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })
      .then((r) => r.data),

  predictMetrics: (metrics: {
    bow_arm_angle: number
    draw_elbow_angle: number
    anchor_jitter: number
    bow_arm_deflection_deg: number
    anchor_duration_sec: number
    release_velocity_px?: number
    torso_tilt_deg?: number
  }) =>
    apiClient
      .post<{ success: boolean; input_features: any; prediction: any }>('/pose/predict-metrics', metrics)
      .then((r) => r.data),

  getStreamUrl: (videoId: string) => `/api/pose/sample-videos/${videoId}/stream`,
}
