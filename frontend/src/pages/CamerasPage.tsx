import { useState, useEffect } from 'react'
import { Camera as CameraIcon, Plus, RefreshCw, Trash2, Settings } from 'lucide-react'
import { useCameraStore } from '@/store/cameraStore'
import { camerasApi } from '@/api/cameras'
import { useSessionStore } from '@/store/sessionStore'
import toast from 'react-hot-toast'
import { cn } from '@/lib/utils'

export default function CamerasPage() {
  const { cameras, setCameras, updateCameraStatus } = useCameraStore()
  const { activeSession } = useSessionStore()
  const [loading, setLoading] = useState(false)

  const loadCameras = async () => {
    if (!activeSession) return
    setLoading(true)
    try {
      const res = await camerasApi.listForSession(activeSession.id)
      setCameras(res.items)
    } catch {
      toast.error('Failed to load cameras')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadCameras()
  }, [activeSession])

  const handleReconnect = async (id: number) => {
    try {
      updateCameraStatus(id, 'connected')
      toast.success('Camera reconnected')
    } catch {
      toast.error('Failed to reconnect')
      updateCameraStatus(id, 'error')
    }
  }

  if (!activeSession) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8 text-center">
        <CameraIcon className="w-16 h-16 text-slate-700 mb-4" />
        <h2 className="text-xl font-semibold text-slate-200 mb-2">No Active Session</h2>
        <p className="text-slate-500 mb-6">Cameras are managed per session. Select an active session first.</p>
      </div>
    )
  }

  return (
    <div className="p-6 h-full flex flex-col animate-in">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Camera Management</h1>
          <p className="text-sm text-slate-500 mt-0.5">Manage and configure assigned cameras</p>
        </div>
        
        <div className="flex gap-2">
          <button onClick={loadCameras} disabled={loading} className="btn-ghost flex items-center gap-2">
            <RefreshCw className={cn("w-4 h-4", loading && "animate-spin")} /> Refresh
          </button>
          <button className="btn-primary flex items-center gap-2">
            <Plus className="w-4 h-4" /> Add Camera
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        {cameras.map(camera => (
          <div key={camera.id} className="glass-card flex flex-col overflow-hidden">
            <div className="bg-black aspect-video relative border-b border-navy-700 flex items-center justify-center">
              <CameraIcon className="w-12 h-12 text-slate-700" />
              <div className="absolute top-2 right-2">
                <span className={cn(
                  "px-2 py-1 text-xs font-medium rounded border",
                  camera.status === 'connected' ? "status-connected" :
                  camera.status === 'error' ? "status-error" : "status-disconnected"
                )}>
                  {camera.status}
                </span>
              </div>
            </div>
            
            <div className="p-4 flex-1 flex flex-col">
              <h3 className="font-semibold text-slate-200">{camera.name}</h3>
              <p className="text-sm text-slate-500 mb-4">Type: {camera.camera_type}</p>
              
              <div className="mt-auto flex items-center justify-between pt-4 border-t border-navy-700">
                <div className="flex gap-2">
                  <button className="btn-ghost p-2" title="Settings">
                    <Settings className="w-4 h-4 text-slate-400" />
                  </button>
                  <button className="btn-ghost p-2 text-red-400 hover:text-red-300" title="Remove">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
                
                {camera.status !== 'connected' && (
                  <button 
                    onClick={() => handleReconnect(camera.id)}
                    className="btn-primary text-sm py-1.5 px-3 flex items-center gap-2"
                  >
                    <RefreshCw className="w-3.5 h-3.5" /> Reconnect
                  </button>
                )}
              </div>
            </div>
          </div>
        ))}

        {cameras.length === 0 && !loading && (
          <div className="col-span-full py-12 text-center text-slate-500 border border-dashed border-navy-700 rounded-xl">
            No cameras configured for this session.
          </div>
        )}
      </div>
    </div>
  )
}
