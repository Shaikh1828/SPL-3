import { useState, useEffect } from 'react'
import { apiClient } from '@/api/client'
import { Image as ImageIcon, Loader2 } from 'lucide-react'

interface AuthenticatedImageProps extends React.ImgHTMLAttributes<HTMLImageElement> {
  src: string
}

export function AuthenticatedImage({ src, className, ...props }: AuthenticatedImageProps) {
  const [blobUrl, setBlobUrl] = useState<string>('')
  const [error, setError] = useState<boolean>(false)
  const [loading, setLoading] = useState<boolean>(true)

  useEffect(() => {
    if (!src) return

    let active = true
    setLoading(true)
    setError(false)

    apiClient
      .get(src, { responseType: 'blob' })
      .then((response) => {
        if (!active) return
        const url = URL.createObjectURL(response.data)
        setBlobUrl(url)
        setLoading(false)
      })
      .catch(() => {
        if (!active) return
        setError(true)
        setLoading(false)
      })

    return () => {
      active = false
      if (blobUrl) {
        URL.revokeObjectURL(blobUrl)
      }
    }
  }, [src])

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center bg-navy-900 border border-navy-800 rounded-lg w-full aspect-video min-h-[300px]">
        <Loader2 className="w-8 h-8 text-gold-500 animate-spin mb-2" />
        <span className="text-xs text-slate-500">Loading protected image...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center bg-navy-900 border border-navy-800 text-slate-500 rounded-lg p-6 w-full aspect-video min-h-[300px]">
        <ImageIcon className="w-12 h-12 text-slate-700 mb-2" />
        <p className="text-sm font-medium">Image Not Available</p>
        <p className="text-xs text-slate-650 mt-1">No captured image exists for this score record.</p>
      </div>
    )
  }

  return <img src={blobUrl} className={className} {...props} />
}
