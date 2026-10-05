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
    if (!src) {
      setLoading(false)
      setError(true)
      return
    }

    // Direct base64 or blob URL
    if (src.startsWith('data:image/') || src.startsWith('blob:')) {
      setBlobUrl(src)
      setLoading(false)
      setError(false)
      return
    }

    let active = true
    setLoading(true)
    setError(false)

    // Normalize endpoint path to avoid double /api/api/
    const endpoint = src.startsWith('/api/') ? src.substring(4) : src

    apiClient
      .get(endpoint, { responseType: 'blob' })
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
      if (blobUrl && blobUrl.startsWith('blob:')) {
        URL.revokeObjectURL(blobUrl)
      }
    }
  }, [src])

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center bg-navy-950 border border-navy-800 rounded-lg w-full h-full min-h-[160px]">
        <Loader2 className="w-6 h-6 text-gold-500 animate-spin mb-1.5" />
        <span className="text-[11px] text-slate-500 font-medium">Loading target image...</span>
      </div>
    )
  }

  if (error || !blobUrl) {
    return (
      <div className="flex flex-col items-center justify-center bg-navy-950 border border-navy-800 text-slate-500 rounded-lg p-4 w-full h-full min-h-[160px]">
        <ImageIcon className="w-8 h-8 text-slate-700 mb-1.5" />
        <p className="text-xs font-semibold text-slate-400">Target Image Preview</p>
        <p className="text-[10px] text-slate-600 mt-0.5">Camera vision frame</p>
      </div>
    )
  }

  return <img src={blobUrl} className={className} {...props} />
}

