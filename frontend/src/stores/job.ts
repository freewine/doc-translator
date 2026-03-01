import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { TranslationJob, JobStatus } from '@/types'
import { apolloClient } from '@/services/apollo'
import { JOB_HISTORY_QUERY } from '@/graphql/queries'

// Filter interface for job history queries
export interface JobHistoryFilters {
  status?: JobStatus
  dateFrom?: string
  dateTo?: string
  limit?: number
}

// Response types for GraphQL query
interface JobHistoryResponse {
  jobHistory: {
    jobs: TranslationJob[]
    nextCursor: string | null
    hasMore: boolean
  }
}

export const useJobStore = defineStore('job', () => {
  // Helper to deep clone objects (removes Apollo's freeze)
  // Apollo Client freezes query/mutation results to prevent cache corruption,
  // so we need to clone before storing/modifying
  function deepClone<T>(obj: T): T {
    return structuredClone(obj)
  }

  // Current session state (in-memory)
  const currentJob = ref<TranslationJob | null>(null)
  const jobs = ref<TranslationJob[]>([])
  const isPolling = ref(false)

  // Pagination state for API-based fetching
  const cursor = ref<string | null>(null)
  const hasMore = ref<boolean>(false)
  const isLoadingHistory = ref<boolean>(false)

  // Computed properties
  const activeJobs = computed(() =>
    jobs.value.filter((job: TranslationJob) =>
      job.status === 'PROCESSING' || job.status === 'PENDING'
    )
  )

  const completedJobs = computed(() =>
    jobs.value.filter((job: TranslationJob) =>
      job.status === 'COMPLETED' ||
      job.status === 'FAILED' ||
      job.status === 'PARTIAL_SUCCESS'
    )
  )

  const hasActiveJob = computed(() => activeJobs.value.length > 0)

  /**
   * Fetch job history from backend API
   * @param filters Optional filters for the query
   * @param append If true, append to existing jobs; if false, replace
   */
  async function fetchJobHistory(filters?: JobHistoryFilters, append: boolean = false): Promise<void> {
    isLoadingHistory.value = true

    try {
      const variables = {
        limit: filters?.limit ?? 20,
        cursor: append ? cursor.value : null,
        status: filters?.status,
        dateFrom: filters?.dateFrom,
        dateTo: filters?.dateTo,
      }

      const result = await apolloClient.query<JobHistoryResponse>({
        query: JOB_HISTORY_QUERY,
        variables,
        fetchPolicy: 'network-only',
      })

      if (result.data?.jobHistory) {
        const { jobs: fetchedJobs, nextCursor, hasMore: moreAvailable } = result.data.jobHistory

        if (append) {
          // Append fetched jobs, avoiding duplicates
          const existingIds = new Set(jobs.value.map(j => j.id))
          const newJobs = fetchedJobs.filter(j => !existingIds.has(j.id)).map(deepClone)
          jobs.value = [...jobs.value, ...newJobs]
        } else {
          // Replace jobs with fetched results (clone to avoid frozen Apollo objects)
          jobs.value = fetchedJobs.map(deepClone)
        }

        cursor.value = nextCursor
        hasMore.value = moreAvailable
      }
    } catch (error) {
      console.error('Failed to fetch job history:', error)
      throw error
    } finally {
      isLoadingHistory.value = false
    }
  }

  /**
   * Load more jobs (pagination)
   */
  async function loadMoreJobs(filters?: JobHistoryFilters): Promise<void> {
    if (!hasMore.value || isLoadingHistory.value) {
      return
    }
    await fetchJobHistory(filters, true)
  }

  /**
   * Reset pagination state
   */
  function resetPagination(): void {
    cursor.value = null
    hasMore.value = false
  }

  /**
   * Set the current active job
   */
  function setCurrentJob(job: TranslationJob) {
    const clonedJob = deepClone(job)
    currentJob.value = clonedJob
    updateJob(clonedJob)
  }

  /**
   * Update a job in the store (in-memory only)
   */
  function updateJob(job: TranslationJob) {
    const clonedJob = deepClone(job)
    const index = jobs.value.findIndex((j: TranslationJob) => j.id === clonedJob.id)
    if (index !== -1) {
      // Create new array to avoid mutating frozen arrays
      jobs.value = [
        ...jobs.value.slice(0, index),
        clonedJob,
        ...jobs.value.slice(index + 1)
      ]
    } else {
      jobs.value = [...jobs.value, clonedJob]
    }

    if (currentJob.value?.id === clonedJob.id) {
      currentJob.value = clonedJob
    }
  }

  /**
   * Add a new job to the store (in-memory only)
   */
  function addJob(job: TranslationJob) {
    // Clone and create new array to avoid mutating frozen Apollo objects
    jobs.value = [deepClone(job), ...jobs.value]
  }

  /**
   * Clear the current job
   */
  function clearCurrentJob() {
    currentJob.value = null
  }

  /**
   * Get a job by ID
   */
  function getJobById(id: string): TranslationJob | undefined {
    return jobs.value.find((job: TranslationJob) => job.id === id)
  }

  /**
   * Remove a job from the store (in-memory only)
   */
  function removeJob(id: string) {
    jobs.value = jobs.value.filter((job: TranslationJob) => job.id !== id)

    if (currentJob.value?.id === id) {
      clearCurrentJob()
    }
  }

  /**
   * Clear all completed jobs (in-memory only)
   */
  function clearCompletedJobs() {
    jobs.value = jobs.value.filter((job: TranslationJob) =>
      job.status === 'PROCESSING' || job.status === 'PENDING'
    )
  }

  /**
   * Clear all jobs (in-memory only)
   */
  function clearAllJobs() {
    jobs.value = []
    clearCurrentJob()
    resetPagination()
  }

  /**
   * Set polling state
   */
  function setPolling(polling: boolean) {
    isPolling.value = polling
  }

  /**
   * Update job status (in-memory only)
   */
  function updateJobStatus(id: string, status: JobStatus) {
    const job = getJobById(id)
    if (job) {
      const updatedJob = { ...job, status }
      if (status === 'COMPLETED' || status === 'FAILED' || status === 'PARTIAL_SUCCESS') {
        updatedJob.completedAt = new Date().toISOString()
      }
      updateJob(updatedJob)
    }
  }

  /**
   * Update job progress (in-memory only)
   */
  function updateJobProgress(id: string, progress: number) {
    const job = getJobById(id)
    if (job) {
      updateJob({ ...job, progress })
    }
  }

  return {
    // State
    currentJob,
    jobs,
    isPolling,
    cursor,
    hasMore,
    isLoadingHistory,

    // Computed
    activeJobs,
    completedJobs,
    hasActiveJob,

    // Actions
    fetchJobHistory,
    loadMoreJobs,
    resetPagination,
    setCurrentJob,
    updateJob,
    addJob,
    clearCurrentJob,
    getJobById,
    removeJob,
    clearCompletedJobs,
    clearAllJobs,
    setPolling,
    updateJobStatus,
    updateJobProgress,
  }
})
