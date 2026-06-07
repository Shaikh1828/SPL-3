import { create } from 'zustand'
import type { Camera } from '@/types'

interface CameraState {
  cameras: Camera[]
  setCameras: (cameras: Camera[]) => void
  updateCameraStatus: (id: number, status: Camera['status']) => void
}

export const useCameraStore = create<CameraState>()((set) => ({
  cameras: [],
  setCameras: (cameras) => set({ cameras }),
  updateCameraStatus: (id, status) =>
    set((state) => ({
      cameras: state.cameras.map((c) => (c.id === id ? { ...c, status } : c)),
    })),
}))
