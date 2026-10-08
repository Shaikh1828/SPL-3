// ─── User & Auth ──────────────────────────────────────────────────────────────

export type UserRole = 'admin' | 'scorer' | 'spectator' | 'archer'

export interface User {
  id: number
  username: string
  email: string
  role: UserRole
  is_active: boolean
  created_at: string
}

export interface AuthResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export interface LoginRequest {
  username: string
  password: string
}

export interface RegisterRequest {
  username: string
  email: string
  password: string
  password_confirm: string
}

// ─── Tournament ───────────────────────────────────────────────────────────────

export interface Tournament {
  id: number
  name: string
  description?: string
  location?: string
  start_date: string
  end_date: string
  created_by?: number
  created_by_user_id?: number
  created_at?: string
  updated_at?: string
  status?: 'ongoing' | 'completed' | 'upcoming'
  total_sessions?: number
  active_sessions?: number
  completed_sessions?: number
  total_archers?: number
  winner_name?: string
  winner_score?: number
}

export interface TournamentCreate {
  name: string
  description?: string
  location?: string
  start_date: string
  end_date: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  skip: number
  limit: number
}

// ─── Session ──────────────────────────────────────────────────────────────────

export type SessionStatus = 'active' | 'paused' | 'completed'

export interface Session {
  id: number
  tournament_id: number
  name: string
  round_number: number
  status: SessionStatus
  start_time?: string
  end_time?: string
  num_lanes: number
  arrows_per_round: number
  archers_count?: number
  scores_count?: number
  created_at: string
  updated_at: string
}

export interface SessionCreate {
  name: string
  round_number: number
  num_lanes: number
  arrows_per_round: number
}

export interface SessionArcher {
  id: number
  session_id: number
  archer_id?: number
  archer_name: string
  lane_number: number
  current_round?: number
  total_score: number
  registered_at?: string
}

export interface SessionArcherCreate {
  archer_name: string
  lane_number: number
}

// ─── Score ────────────────────────────────────────────────────────────────────

export interface Score {
  id: number
  session_id: number
  session_archer_id: number
  round: number
  arrow_num: number
  zone: number
  points: number
  image_id?: string
  validated_by_ai: boolean
  confidence?: number
  method?: string
  created_at: string
  updated_at: string
  annotated_image?: string
}

export interface ScoreCreate {
  session_archer_id: number
  round: number
  arrow_num: number
  zone: number
  points: number
  image_id?: string
}

export interface ScoreValidate {
  validated_by_ai: boolean
  confidence: number
}

// ─── Leaderboard ─────────────────────────────────────────────────────────────

export interface LeaderboardEntry {
  rank: number
  archer_id: number
  archer_name: string
  lane_number: number
  total_score: number
  current_round?: number
  session_archer_id?: number
  round_1_score?: number
  round_2_score?: number
  round_3_score?: number
  arrows_recorded: number
  tens_count?: number
  xs_count?: number
  average_score?: number
  sessions_count?: number
  session_name?: string
  recent_arrows?: number[]
}

export interface Leaderboard {
  session_id: number
  total_archers: number
  items: LeaderboardEntry[]
  cached: boolean
  cache_ttl: number
  last_updated: string
}

// ─── Camera ───────────────────────────────────────────────────────────────────

export type CameraType = 'USB' | 'RTSP' | 'HTTP'
export type CameraStatus = 'connected' | 'disconnected' | 'error'

export interface Camera {
  id: number
  name: string
  camera_type: CameraType
  url?: string
  connection_url?: string
  status: CameraStatus
  lane?: number
  last_heartbeat?: string
  last_connected_at?: string
  created_at: string
  updated_at?: string
}

export interface CameraUpdate {
  name?: string
  camera_type?: CameraType
  url?: string
}

export interface CameraTestResponse {
  connected: boolean
  source: string
  message: string
  resolution?: string
  fps?: number
}

export interface CameraDiscoveryItem {
  device_index: number
  url: string
  camera_type: string
  name: string
  resolution?: string
}

export interface CameraLaneAssignment {
  id: number
  session_id: number
  camera_id: number
  lane: number
  assigned_at: string
}

export interface AssignCameraRequest {
  camera_id: number
  lane: number
}

// ─── Health ───────────────────────────────────────────────────────────────────

export interface HealthStatus {
  status: string
  timestamp: string
  environment?: string
}

export interface DetailedHealth {
  status: string
  timestamp: string
  components: {
    database: { status: string; response_time_ms?: number }
    cache: { status: string; response_time_ms?: number; connected?: boolean }
    storage: { status: string; available_gb?: number; quota_gb?: number; usage_percent?: number }
    threadpool: { status: string; active_threads?: number; max_threads?: number }
  }
}

// ─── WebSocket Events ─────────────────────────────────────────────────────────

export type WSEventType =
  | 'SCORE_RECORDED'
  | 'SCORE_VALIDATED'
  | 'SESSION_STATE_CHANGED'
  | 'LEADERBOARD_UPDATED'
  | 'CAMERA_CONNECTED'
  | 'CAMERA_DISCONNECTED'
  | 'SESSION_CREATED'

export interface WSEvent {
  event_type: WSEventType
  timestamp: string
  data: Record<string, unknown>
}

// ─── System Metrics & Recent Activity ──────────────────────────────────────────

export interface SystemMetrics {
  cpu: {
    cores: number
    load_1m: number
    load_5m: number
    load_15m: number
    approx_utilization_percent: number
  }
  memory: {
    total_mb: number
    available_mb: number
    used_mb: number
    used_percent: number
  }
  storage: {
    status: string
    message: string
    used_gb: number
    quota_gb: number
    usage_percent: number
    disk_total_gb?: number
    disk_used_gb?: number
    disk_free_gb?: number
  }
  ai_engine: {
    model_name: string
    weights_path: string
    weights_found: boolean
    weights_size_mb: number
    device: string
    cuda_available: boolean
    benchmark_map50: number
    benchmark_recall: number
    benchmark_precision: number
    live_confidence_target: string
  }
  database: {
    status: string
    message: string
    timestamp?: string
  }
  cache: {
    status: string
    message: string
    timestamp?: string
  }
  threadpool: {
    status: string
    message: string
    active_workers: number
    max_workers: number
    utilization_percent: number
  }
  runtime: {
    python_version: string
    platform: string
    environment: string
    timestamp: string
  }
}

export interface RecentScoreItem {
  id: number
  session_id: number
  session_archer_id: number
  archer_name: string
  lane_number: number
  round: number
  arrow_number: number
  points: number
  zone: number
  is_x: boolean
  confidence: number
  timestamp?: string | null
}

// ─── AI Round Scoring & Review ────────────────────────────────────────────────

export interface DetectedArrow {
  arrow_num: number
  points: number
  zone: string
  confidence: number
  is_x?: boolean
  tip_x?: number
  tip_y?: number
  is_override?: boolean
  override_reason?: string
}

export interface LaneDetectionResult {
  lane_number: number
  session_archer_id: number
  archer_name: string
  camera_id?: number | null
  camera_name?: string
  camera_status?: string
  status: 'detected' | 'warning' | 'unassigned' | 'overridden'
  detected_arrows: DetectedArrow[]
  end_total: number
  avg_confidence: number
  method: string
  annotated_image?: string | null
}

export interface AIScoreRoundResponse {
  session_id: number
  round: number
  arrows_per_round: number
  lanes: LaneDetectionResult[]
}

export interface LaneSubmission {
  session_archer_id: number
  lane_number: number
  arrows: DetectedArrow[]
}

export interface BatchConfirmRoundRequest {
  round: number
  lane_submissions: LaneSubmission[]
}

export interface BatchConfirmRoundResponse {
  session_id: number
  round: number
  scores_recorded_count: number
  next_round: number
  updated_archers: SessionArcher[]
}

// ─── Analytics & Longitudinal Reports ───────────────────────────────────────────

export interface ZoneCount {
  zone: string
  count: number
  percentage: number
}

export interface EndProgressionItem {
  end: number
  avg_score: number
  total_arrows: number
}

export interface LaneAccuracyItem {
  lane: number
  avg_score: number
  arrows_shot: number
  tens_rate: number
}

export interface AIMetrics {
  total_arrows: number
  ai_validated_percent: number
  avg_confidence: number
  overridden_count: number
}

export interface TournamentAnalyticsResponse {
  tournament_id?: number | null
  tournament_name?: string | null
  session_id?: number | null
  session_name?: string | null
  total_archers: number
  total_arrows_shot: number
  total_points_scored: number
  overall_average_arrow: number
  score_distribution: ZoneCount[]
  end_progression: EndProgressionItem[]
  lane_accuracy: LaneAccuracyItem[]
  ai_metrics: AIMetrics
}

export interface ArcherTournamentHistory {
  tournament_id: number
  tournament_name: string
  location?: string | null
  sessions_count: number
  arrows_shot: number
  total_points: number
  average_arrow: number
  rank: number
  tens_count: number
  xs_count: number
  best_end_score: number
}

export interface ArcherLongitudinalAnalyticsResponse {
  archer_id: number
  archer_name: string
  tournaments_participated: number
  total_career_points: number
  overall_arrow_average: number
  total_tens: number
  total_xs: number
  career_high_end: number
  consistency_index: number
  tournaments: ArcherTournamentHistory[]
  score_distribution: ZoneCount[]
  end_progression: EndProgressionItem[]
}

export interface ArcherDirectoryItem {
  archer_id: number
  archer_name: string
  tournaments_count: number
  total_score: number
  average_arrow: number
}

// ─── Target Image Gallery ───────────────────────────────────────────────────

export interface ScoreGalleryItem {
  id: number
  score_id: number
  session_id: number
  session_name?: string | null
  tournament_id?: number | null
  tournament_name?: string | null
  session_archer_id?: number
  archer_id?: number | null
  archer_name: string
  lane_number: number
  round: number
  arrow_num: number
  zone: number
  points: number
  is_x: boolean
  confidence?: number | null
  method?: string | null
  image_id?: string | null
  image_url: string
  annotated_image_url: string
  created_at: string
}

export interface ScoreGalleryResponse {
  items: ScoreGalleryItem[]
  total: number
  skip: number
  limit: number
}

export interface ScoreGalleryFilterParams {
  tournament_id?: number
  session_id?: number
  archer_id?: number
  archer_name?: string
  round?: number
  min_points?: number
  max_points?: number
  sort_by?: 'latest' | 'oldest' | 'points_desc' | 'points_asc' | 'confidence_desc' | 'confidence_asc' | 'round_asc' | 'round_desc'
  skip?: number
  limit?: number
}

// ─── Archer Pose & Biomechanics Types ────────────────────────────────────────

export interface PoseLandmark {
  id: number
  x: number
  y: number
  z: number
  visibility: number
}

export interface ShotPhaseInfo {
  phase: 'stance' | 'draw' | 'anchor' | 'release'
  name: string
  start_frame: number
  end_frame: number
  start_time: number
  end_time: number
}

export interface CoachingDiagnostic {
  metric: string
  status: 'EXCELLENT' | 'GOOD' | 'NEEDS_WORK' | 'POOR'
  value: string
  target: string
  message: string
  severity?: string
  rule_id?: string
}

export interface PostureAccuracyComponents {
  bow_arm_accuracy_pct: number
  draw_elbow_accuracy_pct: number
  anchor_stability_accuracy_pct: number
  release_follow_through_accuracy_pct: number
  timing_balance_accuracy_pct: number
}

export interface PostureAccuracyData {
  overall_accuracy_pct: number
  accuracy_tier: 'OLYMPIC_ELITE' | 'COMPETITIVE' | 'INTERMEDIATE' | 'DEFICIENT'
  accuracy_label: string
  tier_color: string
  components: PostureAccuracyComponents
}

export interface BiomechanicsScorePrediction {
  predicted_score: number
  score_display: string
  exact_score: number
  is_x_ring: boolean
  score_category: 'Gold' | 'Red' | 'Blue' | 'Black' | 'White'
  category_color: string
  zone_description: string
  form_score_pct: number
  confidence: number
  posture_accuracy?: PostureAccuracyData
  metrics_evaluated: {
    bow_arm_angle: number
    draw_elbow_angle: number
    anchor_jitter_px: number
    bow_arm_deflection_deg: number
    anchor_duration_sec: number
  }
  diagnostics: CoachingDiagnostic[]
}

export interface PoseFrameData {
  frame: number
  time: number
  phase: 'stance' | 'draw' | 'anchor' | 'release'
  landmarks: PoseLandmark[]
}

export interface PoseAnalysisResponse {
  success: boolean
  video_id: string
  title: string
  stream_url?: string
  duration_sec: number
  fps: number
  total_frames: number
  resolution: { width: number; height: number }
  phases: ShotPhaseInfo[]
  biomechanics_summary: {
    avg_bow_arm_angle: number
    avg_draw_elbow_angle: number
    anchor_hold_duration_sec: number
    anchor_jitter_px: number
    bow_arm_deflection_deg: number
    release_frame: number
  }
  prediction: BiomechanicsScorePrediction
  coaching_notes: string[]
  frames_landmarks: PoseFrameData[]
}

export interface SampleVideoItem {
  id: string
  title: string
  filename: string
  expected_score: number
  score_display: string
  category: string
  form_score_pct: number
  description: string
  badge: string
  is_available: boolean
  file_size_bytes: number
  stream_url: string
}

export interface RangeLaneArcherItem {
  lane_number: number
  archer: {
    id: number
    name: string
    category: string
    club: string
    hand: string
    rank: number
    target_number: string
    bow_spec: string
  }
  camera: {
    id: string
    name: string
    type: 'sample' | 'hardware' | 'ip'
    sample_id?: string | null
    status: string
    resolution: string
  }
  baseline_accuracy_pct: number
  accuracy_tier: 'OLYMPIC_ELITE' | 'COMPETITIVE' | 'INTERMEDIATE' | 'DEFICIENT'
  accuracy_label: string
  tier_color: string
  recent_form_notes: string
  default_angles: {
    bow_arm_angle: number
    draw_elbow_angle: number
    anchor_jitter: number
    bow_arm_deflection_deg: number
    anchor_duration_sec: number
  }
}

export interface LiveFrameAnalysisResult {
  success: boolean
  lane_number?: number
  archer_id?: number
  archer_name?: string
  camera_source?: string
  phase?: string
  landmarks: PoseLandmark[]
  metrics: {
    bow_arm_angle: number
    draw_elbow_angle: number
    shoulder_alignment_angle: number
    anchor_jitter_px: number
    bow_arm_deflection_deg: number
    anchor_duration_sec: number
  }
  posture_accuracy: PostureAccuracyData
  predicted_score: number
  score_display: string
  score_category: string
  zone_description: string
  confidence: number
  diagnostics: CoachingDiagnostic[]
}

export interface ArcherPostureRecord {
  record_id: number
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
}

export interface PostureSampleItem {
  filename: string
  file_size_bytes: number
  url: string
}

export interface PostureImageBiomechanics {
  bow_arm_angle: number
  bow_arm_ideal_range: string
  bow_arm_status: 'OPTIMAL' | 'ACCEPTABLE' | 'UNDER_EXTENDED'
  draw_elbow_angle: number
  draw_elbow_ideal_range: string
  draw_elbow_status: 'OPTIMAL' | 'SLIGHT_DEVIATION' | 'FAULT'
  torso_tilt_deg: number
  torso_ideal_range: string
  shoulder_tilt_deg: number
  anchor_hold_jitter_px: number
}

export interface PostureImagePrediction {
  predicted_score: number
  score_display: string
  score_category: string
  zone_description: string
  execution_score_pct: number
  confidence: number
  target_coordinates: { x: number; y: number }
}

export interface PostureImageAnalysisResponse {
  success: boolean
  message?: string
  filename: string
  resolution: { width: number; height: number }
  handedness: 'right' | 'left'
  handedness_label: string
  landmarks: Array<{
    id: number
    x: number
    y: number
    z: number
    visibility: number
  }>
  biomechanics: PostureImageBiomechanics
  prediction: PostureImagePrediction
  posture_accuracy: PostureAccuracyData
  diagnostics: CoachingDiagnostic[]
  coaching_feedback: string[]
  annotated_image_base64: string
  archer_meta?: {
    lane_number?: number
    archer_id?: number
    archer_name?: string
    camera_source?: string
    source?: string
  }
}

export interface PostureSnapshotRequest {
  image_base64: string
  filename?: string
  lane_number?: number
  archer_id?: number
  archer_name?: string
  camera_source?: string
}
