import { ref } from 'vue'
import { api } from '@/services/api'
import { useErrorHandler } from './useErrorHandler'

export interface DownloadProgress {
  filename: string
  isDownloading: boolean
  error: string | null
}

/**
 * Composable for managing file downloads with progress tracking.
 */
export function useFileDownload() {
  const errorHandler = useErrorHandler({ showNotification: true })
  const downloads = ref<Map<string, DownloadProgress>>(new Map())

  const getKey = (jobId: string, filename: string) => `${jobId}:${filename}`

  /**
   * Download a file via presigned S3 URL.
   */
  async function downloadFile(jobId: string, filename: string): Promise<void> {
    const key = getKey(jobId, filename)

    downloads.value.set(key, { filename, isDownloading: true, error: null })

    try {
      // Download file content as blob via backend (works on private networks)
      const blobUrl = await api.downloadFile(jobId, filename)

      // Trigger browser download via blob URL
      const link = document.createElement('a')
      link.href = blobUrl
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)

      // Free the blob URL memory
      URL.revokeObjectURL(blobUrl)

      downloads.value.set(key, { filename, isDownloading: false, error: null })
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Download failed'
      downloads.value.set(key, { filename, isDownloading: false, error: errorMessage })
      errorHandler.handleError(error, 'File Download')
      throw error
    }
  }

  function isDownloading(jobId: string, filename: string): boolean {
    return downloads.value.get(getKey(jobId, filename))?.isDownloading ?? false
  }

  function getDownloadState(jobId: string, filename: string): DownloadProgress | null {
    return downloads.value.get(getKey(jobId, filename)) ?? null
  }

  function clearDownloadState(jobId: string, filename: string): void {
    downloads.value.delete(getKey(jobId, filename))
  }

  function clearAllDownloadStates(): void {
    downloads.value.clear()
  }

  return {
    downloads,
    downloadFile,
    isDownloading,
    getDownloadState,
    clearDownloadState,
    clearAllDownloadStates,
  }
}
