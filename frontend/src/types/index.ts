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
  created_by: number
  created_at: string
  updated_at: string
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
  archer_name: string
  lane_number: number
  total_score: number
  registered_at: string
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
  round_1_score?: number
  round_2_score?: number
  round_3_score?: number
  arrows_recorded: number
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
  connection_url?: string
  status: CameraStatus
  last_heartbeat?: string
  created_at: string
  updated_at: string
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
