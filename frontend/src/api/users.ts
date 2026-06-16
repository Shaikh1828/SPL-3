import { apiClient } from './client'
import type { User } from '@/types'

export interface UserListResponse {
  items: User[]
  total: number
  skip: number
  limit: number
}

export interface UserCreatePayload {
  username: string
  email: string
  password: string
  role: 'admin' | 'scorer' | 'spectator' | 'archer'
}

export interface UserUpdatePayload {
  role?: 'admin' | 'scorer' | 'spectator' | 'archer'
  is_active?: boolean
}

export const usersApi = {
  list: (params?: {
    skip?: number
    limit?: number
    role?: string
    is_active?: boolean
  }): Promise<UserListResponse> =>
    apiClient.get('/users', { params }).then((r) => r.data),

  get: (id: number): Promise<User> =>
    apiClient.get(`/users/${id}`).then((r) => r.data),

  create: (payload: UserCreatePayload): Promise<User> =>
    apiClient.post('/users', payload).then((r) => r.data),

  update: (id: number, payload: UserUpdatePayload): Promise<User> =>
    apiClient.patch(`/users/${id}`, payload).then((r) => r.data),

  deactivate: (id: number): Promise<{ success: boolean; message: string }> =>
    apiClient.delete(`/users/${id}`).then((r) => r.data),
}
