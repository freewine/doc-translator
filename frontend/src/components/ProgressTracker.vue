<template>
  <div class="progress-tracker">
    <!-- Overall Job Progress -->
    <a-card v-if="job" :title="`${t('progress.jobTitle', 'Translation Job')}: ${job.id}`" class="job-card">
      <template #extra>
        <a-tag :color="statusColor">{{ job.status }}</a-tag>
      </template>

      <!-- Overall Progress Bar -->
      <div class="overall-progress">
        <div class="progress-header">
          <span class="progress-label">{{ t('progress.overall') }}</span>
          <span class="progress-stats">
            {{ job.filesCompleted }} / {{ job.filesTotal }} {{ t('progress.filesCompleted') }}
          </span>
        </div>
        <a-progress
          :percent="Math.round(job.progress * 100)"
          :status="progressStatus"
          :stroke-color="progressColor"
        />
      </div>

      <!-- Processing Files -->
      <div v-if="job.filesProcessing.length > 0" class="files-section">
        <h4>{{ t('progress.currentFile') }}</h4>
        <div
          v-for="file in job.filesProcessing"
          :key="file.filename"
          class="file-progress"
        >
          <div class="file-header">
            <a-typography-text strong>{{ file.filename }}</a-typography-text>
            <span class="segment-stats">
              {{ getTranslatedCount(file) }} / {{ getTotalCount(file) }} {{ t('progress.segments', 'segments') }}
            </span>
          </div>
          <a-progress
            :percent="Math.round(file.progress * 100)"
            :show-info="true"
            size="small"
          />
        </div>
      </div>

      <!-- Failed Files -->
      <div v-if="job.filesFailed.length > 0" class="files-section error-section">
        <h4>{{ t('progress.errors') }}</h4>
        <a-alert
          v-for="error in job.filesFailed"
          :key="error.filename"
          :message="error.filename"
          :description="error.error"
          type="error"
          show-icon
          class="error-alert"
        />
      </div>

      <!-- Translation Warnings (segments that failed within completed files) -->
      <div v-if="filesWithWarnings.length > 0" class="files-section warning-section">
        <h4>{{ t('progress.warnings', 'Warnings') }}</h4>
        <a-alert
          v-for="file in filesWithWarnings"
          :key="file.originalFilename"
          :message="file.originalFilename"
          :description="file.translationWarning"
          type="warning"
          show-icon
          class="warning-alert"
        />
      </div>

      <!-- Job Timestamps -->
      <div class="job-info">
        <a-descriptions :column="2" size="small">
          <a-descriptions-item :label="t('progress.started', 'Started')">
            {{ formatDate(job.createdAt) }}
          </a-descriptions-item>
          <a-descriptions-item v-if="job.completedAt" :label="t('progress.completed', 'Completed')">
            {{ formatDate(job.completedAt) }}
          </a-descriptions-item>
        </a-descriptions>
      </div>
    </a-card>

    <!-- Loading State -->
    <a-card v-else-if="loading" class="loading-card">
      <a-spin size="large">
        <template #tip>
          <p>{{ t('progress.loading', 'Loading job status...') }}</p>
        </template>
      </a-spin>
    </a-card>

    <!-- No Job State -->
    <a-empty v-else :description="t('progress.noActiveJob', 'No active translation job')" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { apolloClient } from '@/services/apollo'
import { JOB_QUERY } from '@/graphql/queries'
import { useErrorHandler, isTransientError } from '@/composables/useErrorHandler'
import { useLanguage } from '@/composables/useLanguage'
import type { TranslationJob } from '@/types'
import { JobStatus } from '@/types'

interface Props {
  jobId?: string
  pollInterval?: number
}

const props = withDefaults(defineProps<Props>(), {
  pollInterval: 2000, // 2 seconds default
})

const emit = defineEmits<{
  complete: [job: TranslationJob]
  error: [error: Error]
}>()

// Composables
const errorHandler = useErrorHandler({ 
  showNotification: true,
  retryable: true,
  maxRetries: 3,
})
const { t } = useLanguage()

// State
const job = ref<TranslationJob | null>(null)
const loading = ref(false)
const error = ref<Error | null>(null)
let pollInterval: number | null = null

// Files that completed but had segment-level translation failures
const filesWithWarnings = computed(() =>
  (job.value?.completedFiles ?? []).filter(f => f.segmentsFailed && f.segmentsFailed > 0)
)

// Determine if we should continue polling
const shouldPoll = computed(() => {
  if (!job.value) return false
  const activeStatuses: JobStatus[] = [JobStatus.PENDING, JobStatus.PROCESSING]
  return activeStatuses.includes(job.value.status)
})

// Fetch job status
async function fetchJobStatus() {
  if (!props.jobId) return

  loading.value = true
  error.value = null

  try {
    const result = await apolloClient.query<{ job: TranslationJob }>({
      query: JOB_QUERY,
      variables: { id: props.jobId },
      fetchPolicy: 'network-only',
    })

    if (result.data?.job) {
      job.value = result.data.job
    }
  } catch (err: any) {
    error.value = err
  } finally {
    loading.value = false
  }
}

// Refetch function for manual refresh
async function refetch() {
  await fetchJobStatus()
}

// Status color mapping
const statusColor = computed(() => {
  if (!job.value) return 'default'
  switch (job.value.status) {
    case JobStatus.PENDING:
      return 'blue'
    case JobStatus.PROCESSING:
      return 'orange'
    case JobStatus.COMPLETED:
      return 'green'
    case JobStatus.FAILED:
      return 'red'
    case JobStatus.PARTIAL_SUCCESS:
      return 'gold'
    default:
      return 'default'
  }
})

// Progress status for Ant Design Progress component
const progressStatus = computed(() => {
  if (!job.value) return undefined
  switch (job.value.status) {
    case JobStatus.COMPLETED:
      return 'success'
    case JobStatus.FAILED:
      return 'exception'
    case JobStatus.PROCESSING:
      return 'active'
    default:
      return undefined
  }
})

// Progress color
const progressColor = computed(() => {
  if (!job.value) return undefined
  switch (job.value.status) {
    case JobStatus.PROCESSING:
      return '#1890ff'
    case JobStatus.COMPLETED:
      return '#52c41a'
    case JobStatus.FAILED:
      return '#ff4d4f'
    case JobStatus.PARTIAL_SUCCESS:
      return '#faad14'
    default:
      return undefined
  }
})

// Format date helper
const formatDate = (dateString: string) => {
  const date = new Date(dateString)
  return date.toLocaleString()
}

// Get translated count (prefer segments, fallback to cells for backward compatibility)
function getTranslatedCount(file: { segmentsTranslated?: number; cellsTranslated?: number }): number {
  return file.segmentsTranslated ?? file.cellsTranslated ?? 0
}

// Get total count (prefer segments, fallback to cells for backward compatibility)
function getTotalCount(file: { segmentsTotal?: number; cellsTotal?: number }): number {
  return file.segmentsTotal ?? file.cellsTotal ?? 0
}

// Start polling
function startPolling() {
  if (pollInterval) {
    clearInterval(pollInterval)
  }

  // Initial fetch
  fetchJobStatus()

  // Set up polling
  pollInterval = window.setInterval(() => {
    if (shouldPoll.value) {
      fetchJobStatus()
    } else {
      stopPolling()
    }
  }, props.pollInterval)
}

// Stop polling
function stopPolling() {
  if (pollInterval) {
    clearInterval(pollInterval)
    pollInterval = null
  }
}

// Watch for job completion
watch(
  () => job.value?.status,
  (newStatus, oldStatus) => {
    if (!job.value) return

    // Emit complete event when job finishes
    const finishedStatuses: JobStatus[] = [
      JobStatus.COMPLETED,
      JobStatus.FAILED,
      JobStatus.PARTIAL_SUCCESS,
    ]
    
    if (newStatus && finishedStatuses.includes(newStatus) && oldStatus !== newStatus) {
      emit('complete', job.value)
      stopPolling()
    }
  }
)

// Watch for errors
watch(error, async (newError) => {
  if (newError) {
    emit('error', newError)
    
    // Handle transient errors with retry
    if (isTransientError(newError)) {
      await errorHandler.handleErrorWithRetry(
        newError,
        async () => {
          await refetch()
        },
        'Job Status Polling'
      )
    } else {
      errorHandler.handleError(newError, 'Job Status')
    }
  }
})

// Watch for jobId changes
watch(
  () => props.jobId,
  (newJobId) => {
    if (newJobId) {
      startPolling()
    } else {
      stopPolling()
      job.value = null
    }
  }
)

// Start polling on mount if jobId is provided
onMounted(() => {
  if (props.jobId) {
    startPolling()
  }
})

// Cleanup on unmount
onUnmounted(() => {
  stopPolling()
})

// Expose refetch method for manual refresh
defineExpose({
  refetch,
})
</script>

<style scoped>
.progress-tracker {
  width: 100%;
}

.job-card {
  margin-bottom: 16px;
}

.loading-card {
  text-align: center;
  padding: 40px 0;
}

.overall-progress {
  margin-bottom: 24px;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.progress-label {
  font-weight: 500;
  font-size: 14px;
}

.progress-stats {
  color: rgba(0, 0, 0, 0.45);
  font-size: 13px;
}

.files-section {
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
}

.files-section h4 {
  margin-bottom: 16px;
  font-size: 14px;
  font-weight: 500;
}

.file-progress {
  margin-bottom: 16px;
}

.file-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.segment-stats {
  color: rgba(0, 0, 0, 0.45);
  font-size: 12px;
}

.error-section {
  border-top-color: #ffccc7;
}

.warning-section {
  border-top-color: #ffe58f;
}

.warning-alert {
  margin-bottom: 12px;
}

.warning-alert:last-child {
  margin-bottom: 0;
}

.error-alert {
  margin-bottom: 12px;
}

.error-alert:last-child {
  margin-bottom: 0;
}

.job-info {
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
}

/* Loading animation */
:deep(.ant-spin-dot) {
  font-size: 32px;
}

/* Mobile layout (< 768px) */
@media (max-width: 767px) {
  .job-card :deep(.ant-card-head) {
    padding: 12px 16px;
  }

  .job-card :deep(.ant-card-head-title) {
    font-size: 14px;
  }

  .job-card :deep(.ant-card-body) {
    padding: 16px;
  }

  .overall-progress {
    margin-bottom: 20px;
  }

  .progress-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 6px;
    margin-bottom: 10px;
  }

  .progress-label {
    font-size: 13px;
  }

  .progress-stats {
    font-size: 12px;
  }

  .files-section {
    margin-top: 20px;
    padding-top: 12px;
  }

  .files-section h4 {
    font-size: 13px;
    margin-bottom: 12px;
  }

  .file-progress {
    margin-bottom: 12px;
  }

  .file-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 6px;
    margin-bottom: 10px;
  }

  .file-header :deep(.ant-typography) {
    font-size: 13px;
  }

  .cell-stats {
    font-size: 11px;
  }

  .error-alert {
    margin-bottom: 10px;
  }

  .error-alert :deep(.ant-alert-message) {
    font-size: 13px;
  }

  .error-alert :deep(.ant-alert-description) {
    font-size: 12px;
  }

  .job-info {
    margin-top: 20px;
    padding-top: 12px;
  }

  .job-info :deep(.ant-descriptions-item-label),
  .job-info :deep(.ant-descriptions-item-content) {
    font-size: 12px;
  }

  .loading-card {
    padding: 30px 0;
  }

  .loading-card :deep(.ant-spin-text) {
    font-size: 13px;
  }
}

/* Tablet layout (768px - 1024px) */
@media (min-width: 768px) and (max-width: 1024px) {
  .job-card :deep(.ant-card-head) {
    padding: 14px 20px;
  }

  .job-card :deep(.ant-card-body) {
    padding: 20px;
  }

  .progress-header {
    gap: 8px;
  }

  .progress-label {
    font-size: 13px;
  }

  .files-section h4 {
    font-size: 13px;
  }

  .file-header {
    gap: 8px;
  }
}

/* Desktop layout (> 1024px) */
@media (min-width: 1025px) {
  .job-card :deep(.ant-card-head) {
    padding: 16px 24px;
  }

  .job-card :deep(.ant-card-body) {
    padding: 24px;
  }
}

/* Small mobile devices */
@media (max-width: 480px) {
  .job-card :deep(.ant-card-head) {
    padding: 10px 12px;
  }

  .job-card :deep(.ant-card-head-title) {
    font-size: 13px;
  }

  .job-card :deep(.ant-card-body) {
    padding: 12px;
  }

  .overall-progress {
    margin-bottom: 16px;
  }

  .progress-header {
    gap: 4px;
    margin-bottom: 8px;
  }

  .progress-label {
    font-size: 12px;
  }

  .progress-stats {
    font-size: 11px;
  }

  .files-section {
    margin-top: 16px;
    padding-top: 10px;
  }

  .files-section h4 {
    font-size: 12px;
    margin-bottom: 10px;
  }

  .file-progress {
    margin-bottom: 10px;
  }

  .file-header {
    gap: 4px;
    margin-bottom: 8px;
  }

  .file-header :deep(.ant-typography) {
    font-size: 12px;
  }

  .cell-stats {
    font-size: 10px;
  }

  .job-info {
    margin-top: 16px;
    padding-top: 10px;
  }

  .job-info :deep(.ant-descriptions-item-label),
  .job-info :deep(.ant-descriptions-item-content) {
    font-size: 11px;
  }
}

/* Landscape orientation on mobile */
@media (max-height: 600px) and (orientation: landscape) {
  .job-card :deep(.ant-card-head) {
    padding: 10px 16px;
  }

  .job-card :deep(.ant-card-body) {
    padding: 12px 16px;
  }

  .overall-progress {
    margin-bottom: 12px;
  }

  .files-section {
    margin-top: 12px;
    padding-top: 8px;
  }

  .file-progress {
    margin-bottom: 8px;
  }
}
</style>
