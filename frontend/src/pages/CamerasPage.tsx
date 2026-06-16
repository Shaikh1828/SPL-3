import { useState, useEffect } from 'react'
import { Camera as CameraIcon, Plus, RefreshCw, Trash2, Settings, X } from 'lucide-react'
import { useCameraStore } from '@/store/cameraStore'
import { camerasApi } from '@/api/cameras'
import { useSessionStore } from '@/store/sessionStore'
import toast from 'react-hot-toast'
import { cn } from '@/lib/utils'
import type { Camera } from '@/types'

export default function CamerasPage() {
  const { cameras, setCameras, updateCameraStatus } = useCameraStore()
  const { activeSession } = useSessionStore()
  const [loading, setLoading] = useState(false)

  // Modals and global list state
  const [isAddCameraOpen, setIsAddCameraOpen] = useState(false)
  const [globalCameras, setGlobalCameras] = useState<Camera[]>([])
  const [selectedGlobalCameraId, setSelectedGlobalCameraId] = useState<number | string>('')
  const [assignedLane, setAssignedLane] = useState<number>(1)

  // Subform for registering a new camera globally
  const [showRegisterForm, setShowRegisterForm] = useState(false)
  const [newCameraData, setNewCameraData] = useState({
    name: '',
    camera_type: 'RTSP',
    url: '',
  })

  const loadCameras = async () => {
    if (!activeSession) return
    setLoading(true)
    try {
      const res = await camerasApi.listForSession(activeSession.id)
      const list = Array.isArray(res) ? res : (res && Array.isArray((res as any).items) ? (res as any).items : [])
      setCameras(list)
    } catch {
      toast.error('Failed to load cameras')
    } finally {
      setLoading(false)
    }
  }

  const loadGlobalCameras = async () => {
    try {
      const res = await camerasApi.listGlobal()
      setGlobalCameras(res || [])
    } catch {
      toast.error('Failed to load global cameras list')
    }
  }

  const handleOpenAddModal = () => {
    setIsAddCameraOpen(true)
    loadGlobalCameras()
  }

  const handleAssignCamera = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!activeSession) return
    const camId = parseInt(selectedGlobalCameraId as string)
    if (!camId) {
      toast.error('Please select a camera')
      return
    }
    try {
      await camerasApi.assign(activeSession.id, {
        camera_id: camId,
        lane: assignedLane,
      })
      toast.success('Camera assigned successfully')
      setIsAddCameraOpen(false)
      setSelectedGlobalCameraId('')
      setAssignedLane(1)
      loadCameras()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to assign camera')
    }
  }

  const handleRegisterCamera = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newCameraData.name || !newCameraData.url) {
      toast.error('Please fill in required fields')
      return
    }
    try {
      const newCam = await camerasApi.create(newCameraData)
      toast.success('Camera registered globally')
      setNewCameraData({ name: '', camera_type: 'RTSP', url: '' })
      setShowRegisterForm(false)
      await loadGlobalCameras()
      setSelectedGlobalCameraId(newCam.id)
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to register camera')
    }
  }

  const handleUnassignCamera = async (cameraId: number) => {
    if (!activeSession) return
    if (!window.confirm('Are you sure you want to remove this camera from this session?')) return
    try {
      await camerasApi.unassign(activeSession.id, cameraId)
      toast.success('Camera removed from session')
      loadCameras()
    } catch {
      toast.error('Failed to remove camera')
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
          <button onClick={handleOpenAddModal} className="btn-primary flex items-center gap-2">
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
                  <button 
                    onClick={() => handleUnassignCamera(camera.id)}
                    className="btn-ghost p-2 text-red-400 hover:text-red-300" 
                    title="Remove"
                  >
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

      {/* Add Camera Modal */}
      {isAddCameraOpen && (
        <div className="fixed inset-0 bg-navy-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="glass-card max-w-md w-full p-6 space-y-4 animate-in">
            <div className="flex justify-between items-center pb-2 border-b border-navy-700">
              <h3 className="text-lg font-bold text-slate-100">Add Camera to Session</h3>
              <button 
                onClick={() => { setIsAddCameraOpen(false); setShowRegisterForm(false); }} 
                className="text-slate-400 hover:text-slate-200"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {!showRegisterForm ? (
              <form onSubmit={handleAssignCamera} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1.5">Select Camera *</label>
                  <select
                    required
                    value={selectedGlobalCameraId}
                    onChange={e => setSelectedGlobalCameraId(e.target.value)}
                    className="input-dark w-full"
                  >
                    <option value="">-- Choose registered camera --</option>
                    {globalCameras
                      .filter(gc => !cameras.some(c => c.id === gc.id))
                      .map(gc => (
                        <option key={gc.id} value={gc.id}>
                          {gc.name} ({gc.camera_type})
                        </option>
                      ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1.5">Assign to Lane (1-{activeSession.num_lanes}) *</label>
                  <input
                    type="number"
                    required
                    min="1"
                    max={activeSession.num_lanes}
                    value={assignedLane}
                    onChange={e => setAssignedLane(parseInt(e.target.value) || 1)}
                    className="input-dark w-full"
                  />
                </div>

                <div className="flex items-center justify-between pt-2 border-t border-navy-700">
                  <button
                    type="button"
                    onClick={() => setShowRegisterForm(true)}
                    className="text-xs text-gold-400 hover:text-gold-300 font-semibold"
                  >
                    + Register a new camera
                  </button>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => setIsAddCameraOpen(false)}
                      className="btn-ghost py-1.5 px-3 text-sm"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      className="btn-primary py-1.5 px-3 text-sm"
                    >
                      Assign Camera
                    </button>
                  </div>
                </div>
              </form>
            ) : (
              <form onSubmit={handleRegisterCamera} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1.5">Camera Name *</label>
                  <input
                    type="text"
                    required
                    value={newCameraData.name}
                    onChange={e => setNewCameraData(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="e.g. Lane 1 target camera"
                    className="input-dark w-full"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1.5">Camera Type *</label>
                    <select
                      required
                      value={newCameraData.camera_type}
                      onChange={e => setNewCameraData(prev => ({ ...prev, camera_type: e.target.value }))}
                      className="input-dark w-full"
                    >
                      <option value="USB">USB</option>
                      <option value="RTSP">RTSP</option>
                      <option value="HTTP">HTTP (MJPEG)</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1.5">Stream URL / Path *</label>
                    <input
                      type="text"
                      required
                      value={newCameraData.url}
                      onChange={e => setNewCameraData(prev => ({ ...prev, url: e.target.value }))}
                      placeholder={newCameraData.camera_type === 'USB' ? '/dev/video0' : 'rtsp://...'}
                      className="input-dark w-full"
                    />
                  </div>
                </div>

                <div className="flex justify-end gap-3 pt-2 border-t border-navy-700">
                  <button
                    type="button"
                    onClick={() => setShowRegisterForm(false)}
                    className="btn-ghost py-1.5 px-3 text-sm"
                  >
                    Back to Assignment
                  </button>
                  <button
                    type="submit"
                    className="btn-primary py-1.5 px-3 text-sm"
                  >
                    Register Camera
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
