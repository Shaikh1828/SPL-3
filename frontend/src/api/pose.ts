import { apiClient } from './client'
import type {
  SampleVideoItem,
  PoseAnalysisResponse,
  PostureSampleItem,
  PostureImageAnalysisResponse,
  PostureSnapshotRequest
} from '@/types'

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

  // ─── Posture Benchmark Images & Camera Snapshots ─────────────────────────
  getPostureSamples: () =>
    apiClient
      .get<{ success: boolean; total: number; samples: PostureSampleItem[] }>('/pose/posture-samples')
      .then((r) => r.data),

  getPostureSampleUrl: (filename: string) => `/api/pose/posture-samples/${encodeURIComponent(filename)}`,

  analyzePostureSample: (
    filename: string,
    meta?: { lane_number?: number; archer_id?: number; archer_name?: string }
  ) =>
    apiClient
      .post<PostureImageAnalysisResponse>(
        `/pose/posture-samples/${encodeURIComponent(filename)}/analyze`,
        null,
        { params: meta }
      )
      .then((r) => r.data),

  analyzeUploadedImage: (formData: FormData) =>
    apiClient
      .post<PostureImageAnalysisResponse>('/pose/analyze-image', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })
      .then((r) => r.data),

  analyzeCameraSnapshot: (data: PostureSnapshotRequest) =>
    apiClient
      .post<PostureImageAnalysisResponse>('/pose/analyze-snapshot', data)
      .then((r) => r.data),

  analyzeLaneCamera: (laneNumber: number, sessionId?: number) =>
    apiClient
      .post<PostureImageAnalysisResponse>(`/pose/lane/${laneNumber}/analyze-camera`, null, {
        params: sessionId ? { session_id: sessionId } : undefined,
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

  evaluatePosture: (data: {
    bow_arm_angle: number
    draw_elbow_angle: number
    anchor_jitter: number
    bow_arm_deflection_deg: number
    anchor_duration_sec: number
    camera_source?: string
  }) =>
    apiClient
      .post<{
        success: boolean
        camera_source: string
        overall_accuracy_pct: number
        accuracy_tier: string
        accuracy_label: string
        tier_color: string
        components: any
        diagnostics: any[]
        predicted_score: number
        score_display: string
      }>('/pose/evaluate-posture', data)
      .then((r) => r.data),

  getLanesAndArchers: () =>
    apiClient
      .get<{ success: boolean; total_lanes: number; lanes: any[] }>('/pose/lanes-and-archers')
      .then((r) => r.data),

  analyzeLiveFrame: (data: {
    lane_number?: number
    archer_id?: number
    archer_name?: string
    camera_source?: string
    phase?: string
    bow_arm_angle?: number
    draw_elbow_angle?: number
    anchor_jitter?: number
    bow_arm_deflection_deg?: number
    anchor_duration_sec?: number
    frame_base64?: string
  }) =>
    apiClient
      .post<any>('/pose/analyze-live-frame', data)
      .then((r) => r.data),

  recordArcherPosture: (data: {
    archer_id: number
    archer_name: string
    lane_number: number
    camera_source: string
    overall_accuracy_pct: number
    accuracy_tier: string
    predicted_score: number
    bow_arm_angle: number
    draw_elbow_angle: number
    notes?: string
  }) =>
    apiClient
      .post<{ success: boolean; record: any }>('/pose/record-archer-posture', data)
      .then((r) => r.data),

  getArcherPostureHistory: (archerId: number) =>
    apiClient
      .get<{ success: boolean; archer_id: number; total_records: number; records: any[] }>(
        `/pose/archer/${archerId}/history`
      )
      .then((r) => r.data),

  getStreamUrl: (videoId: string) => `/api/pose/sample-videos/${videoId}/stream`,
}
