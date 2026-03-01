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

  // Helper to create consistent keys
  const getKey = (jobId: string, filename: string) => `${jobId}:${filename}`

  /**
   * Download a file and trigger browser download.
   */
  async function downloadFile(jobId: string, filename: string): Promise<void> {
    const key = getKey(jobId, filename)

    downloads.value.set(key, { filename, isDownloading: true, error: null })

    try {
      const blob = await api.downloadFile(jobId, filename)

      // Trigger browser download
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)

      downloads.value.set(key, { filename, isDownloading: false, error: null })
      errorHandler.showSuccess(`Downloaded ${filename}`)
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Download failed'
      downloads.value.set(key, { filename, isDownloading: false, error: errorMessage })
      errorHandler.handleError(error, 'File Download')
      throw error
    }
  }

  /**
   * Check if a file is currently downloading.
   */
  function isDownloading(jobId: string, filename: string): boolean {
    return downloads.value.get(getKey(jobId, filename))?.isDownloading ?? false
  }

  /**
   * Get download state for a specific file.
   */
  function getDownloadState(jobId: string, filename: string): DownloadProgress | null {
    return downloads.value.get(getKey(jobId, filename)) ?? null
  }

  /**
   * Clear download state for a file.
   */
  function clearDownloadState(jobId: string, filename: string): void {
    downloads.value.delete(getKey(jobId, filename))
  }

  /**
   * Clear all download states.
   */
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
