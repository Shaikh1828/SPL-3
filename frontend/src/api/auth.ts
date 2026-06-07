import { apiClient } from './client'
import type { AuthResponse, LoginRequest, RegisterRequest, User } from '@/types'

export const authApi = {
  login: (data: LoginRequest) =>
    apiClient.post<AuthResponse>('/auth/login', data).then((r) => r.data),

  register: (data: RegisterRequest) =>
    apiClient.post<User>('/auth/register', data).then((r) => r.data),

  refresh: (refreshToken: string) =>
    apiClient
      .post<AuthResponse>('/auth/refresh', null, {
        headers: { Authorization: `Bearer ${refreshToken}` },
      })
      .then((r) => r.data),

  resetPassword: (currentPassword: string, newPassword: string) =>
    apiClient
      .post('/auth/reset-password', {
        current_password: currentPassword,
        new_password: newPassword,
      })
      .then((r) => r.data),
}
