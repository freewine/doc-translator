/**
 * API service for non-GraphQL operations (file downloads).
 * GraphQL operations should use the composables in useGraphQL.ts
 * with queries/mutations from the graphql/ folder.
 */

export const api = {
  /**
   * Download a translated file from the server.
   */
  async downloadFile(jobId: string, filename: string): Promise<Blob> {
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/graphql'
    const downloadUrl = apiUrl.replace('/graphql', '/download')
    const token = localStorage.getItem('auth_token')

    if (!token) {
      throw new Error('Authentication required')
    }

    const url = `${downloadUrl}?job_id=${encodeURIComponent(jobId)}&filename=${encodeURIComponent(filename)}`

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: 'Download failed' }))
      throw new Error(error.error || `Download failed with status ${response.status}`)
    }

    return response.blob()
  },
}
