<template>
  <div class="main-page">
    <div class="content">
      <div class="page-header">
        <h1>{{ t('translation.title', 'Translation Dashboard') }}</h1>
        <p class="subtitle">{{ t('translation.subtitle', 'Upload your documents and translate them instantly.') }}</p>
      </div>

      <!-- Use Ant Design Grid System for responsive layout -->
      <a-row :gutter="[24, 24]">
        <!-- File Upload Section -->
        <a-col :xs="24" :sm="24" :md="24" :lg="24" :xl="24">
          <a-card :bordered="false" class="section-card glass-card upload-card">
            <template #title>
              <div class="card-header">
                <FileOutlined class="header-icon" />
                <span>{{ t('fileUpload.title') }}</span>
              </div>
            </template>
            <FileUploader
              ref="fileUploaderRef"
              @files-changed="handleFilesChanged"
              @upload-error="handleUploadError"
            />
          </a-card>
        </a-col>

        <!-- Language Pair and Term Catalogs - Side by side on larger screens -->
        <a-col :xs="24" :sm="24" :md="12" :lg="12" :xl="12">
          <a-card :bordered="false" class="section-card glass-card">
            <template #title>
              <div class="card-header">
                <GlobalOutlined class="header-icon" />
                <span>{{ t('languagePair.title') }}</span>
              </div>
            </template>
            <LanguagePairSelector
              ref="languagePairSelectorRef"
              v-model="selectedLanguagePairId"
              @change="handleLanguagePairChange"
              @error="handleLanguagePairError"
            />
          </a-card>
        </a-col>

        <a-col :xs="24" :sm="24" :md="12" :lg="12" :xl="12">
          <a-card :bordered="false" class="section-card glass-card" :class="{ 'disabled-card': !selectedLanguagePairId }">
            <template #title>
              <div class="card-header">
                <BookOutlined class="header-icon" />
                <span>{{ t('thesaurus.termCatalogs', 'Term Catalogs') }}</span>
                <span class="optional-badge">{{ t('common.optional', 'Optional') }}</span>
              </div>
            </template>
            <div v-if="!selectedLanguagePairId" class="placeholder-content">
              <a-empty :description="t('thesaurus.selectLanguagePairFirst', 'Select a language pair first')" :image="false" />
            </div>
            <CatalogSelector
              v-else
              v-model="selectedCatalogIds"
              :language-pair-id="selectedLanguagePairId"
            />
          </a-card>
        </a-col>

        <!-- Start Translation - Full width after the two cards above -->
        <a-col :xs="24" :sm="24" :md="24" :lg="24" :xl="24">
          <a-card :bordered="false" class="section-card glass-card action-card">
            <template #title>
              <div class="card-header">
                <ThunderboltOutlined class="header-icon" />
                <span>{{ t('translation.start') }}</span>
              </div>
            </template>
            <div class="job-controls">
              <div class="action-description">
                {{ t('translation.actionDescription', 'Ready to translate? Click below to start the process.') }}
              </div>
              <div class="output-mode-selector">
                <span class="selector-label">{{ t('outputMode.label') }}</span>
                <a-tooltip :title="t('outputMode.tooltip')">
                  <QuestionCircleOutlined class="help-icon" />
                </a-tooltip>
                <a-radio-group v-model:value="outputMode" class="output-mode-radio-group">
                  <a-radio value="replace">{{ t('outputMode.replace') }}</a-radio>
                  <a-radio value="append">{{ t('outputMode.append') }}</a-radio>
                  <a-radio value="interleaved">{{ t('outputMode.interleaved') }}</a-radio>
                </a-radio-group>
              </div>
              <a-button
                type="primary"
                size="large"
                :disabled="!canStartJob"
                :loading="isCreatingJob"
                @click="handleStartTranslation"
                block
                class="start-button"
              >
                <template #icon>
                  <PlayCircleOutlined />
                </template>
                {{ t('translation.start') }}
              </a-button>
              <div v-if="!canStartJob" class="validation-message">
                <a-alert
                  :message="validationMessage"
                  type="info"
                  show-icon
                  class="info-alert"
                >
                  <template #icon><InfoCircleOutlined /></template>
                </a-alert>
              </div>
            </div>
          </a-card>
        </a-col>

        <!-- Progress Tracking Section -->
        <a-col v-if="currentJob" :xs="24" :sm="24" :md="24" :lg="24" :xl="24">
          <a-card :bordered="false" class="section-card glass-card highlight-card">
             <template #title>
              <div class="card-header">
                <SyncOutlined spin class="header-icon" />
                <span>{{ t('progress.title') }}</span>
              </div>
            </template>
            <ProgressTracker
              :job-id="currentJob.id"
              @complete="handleJobComplete"
              @error="handleProgressError"
            />
          </a-card>
        </a-col>

        <!-- Completed Jobs Section -->
        <a-col :xs="24" :sm="24" :md="24" :lg="24" :xl="24">
          <a-card :bordered="false" title="Recent History" class="section-card glass-card history-card">
             <template #title>
              <div class="card-header">
                <HistoryOutlined class="header-icon" />
                <span>{{ t('job.history', 'Recent History') }}</span>
              </div>
            </template>
            
            <div v-if="completedJobs.length === 0" class="empty-state">
              <a-empty :description="t('job.noJobs', 'No completed jobs yet')" />
            </div>

            <a-list v-else :data-source="completedJobs" item-layout="vertical" class="job-list">
              <template #renderItem="{ item }">
                <a-list-item class="job-item">
                  <div class="job-item-content">
                    <div class="job-header">
                        <div class="job-title-row">
                             <a-tag :color="getStatusColor(item.status)" class="status-tag">
                                {{ item.status }}
                             </a-tag>
                             <span class="job-id">#{{ item.id }}</span>
                             <span class="job-date">{{ formatDate(item.createdAt) }}</span>
                        </div>
                         <div class="job-stats">
                             <span class="stat"><FileOutlined /> {{ item.filesCompleted }} / {{ item.filesTotal }} {{ t('job.files', 'files') }}</span>
                         </div>
                    </div>

                    <!-- Download Section -->
                    <div class="download-section" v-if="item.status === 'COMPLETED' || item.status === 'PARTIAL_SUCCESS'">
                      <div class="files-grid">
                        <div
                          v-for="file in getCompletedFiles(item)"
                          :key="file.filename"
                          class="file-download-card"
                        >
                            <div class="file-icon-wrapper">
                                <FileExcelOutlined v-if="getDocumentTypeFromFilename(file.filename) === DocType.EXCEL" class="doc-icon" :style="{ color: getDocumentIconColor(DocType.EXCEL) }" />
                                <FileWordOutlined v-else-if="getDocumentTypeFromFilename(file.filename) === DocType.WORD" class="doc-icon" :style="{ color: getDocumentIconColor(DocType.WORD) }" />
                                <FilePptOutlined v-else-if="getDocumentTypeFromFilename(file.filename) === DocType.POWERPOINT" class="doc-icon" :style="{ color: getDocumentIconColor(DocType.POWERPOINT) }" />
                                <FilePdfOutlined v-else-if="getDocumentTypeFromFilename(file.filename) === DocType.PDF" class="doc-icon" :style="{ color: getDocumentIconColor(DocType.PDF) }" />
                                <FileOutlined v-else class="doc-icon" :style="{ color: '#8c8c8c' }" />
                            </div>
                            <div class="file-info">
                                <div class="filename" :title="file.filename">{{ file.filename }}</div>
                                <a-button
                                    type="text"
                                    size="small"
                                    class="download-btn"
                                    :loading="fileDownload.isDownloading(item.id, file.filename)"
                                    @click="handleDownload(item.id, file.filename)"
                                >
                                    {{ t('download.button') }}
                                </a-button>
                            </div>
                        </div>
                      </div>
                    </div>

                    <!-- Failed files -->
                    <div
                      v-if="item.filesFailed && item.filesFailed.length > 0"
                      class="failed-files-section"
                    >
                      <div class="failed-header">{{ t('job.failedFiles', 'Failed Files') }}</div>
                      <div
                        v-for="file in item.filesFailed"
                        :key="file.filename"
                        class="failed-file"
                      >
                        <CloseCircleOutlined class="error-icon" />
                        <span class="filename">{{ file.filename }}</span>
                        <span class="error-text">{{ file.error }}</span>
                      </div>
                    </div>
                  </div>
                </a-list-item>
              </template>
            </a-list>
          </a-card>
        </a-col>
      </a-row>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, defineAsyncComponent } from 'vue'
import { useJobStore } from '@/stores/job'
import { useErrorHandler } from '@/composables/useErrorHandler'
import { useLoading } from '@/composables/useLoading'
import { useFileDownload } from '@/composables/useFileDownload'
import { useLanguage } from '@/composables/useLanguage'
import { useMutation } from '@/composables/useGraphQL'
import { CREATE_TRANSLATION_JOB_MUTATION } from '@/graphql/mutations'
import {
  PlayCircleOutlined,
  FileOutlined,
  FileExcelOutlined,
  FileWordOutlined,
  FilePptOutlined,
  FilePdfOutlined,
  CloseCircleOutlined,
  InfoCircleOutlined,
  GlobalOutlined,
  ThunderboltOutlined,
  HistoryOutlined,
  SyncOutlined,
  BookOutlined,
  QuestionCircleOutlined
} from '@ant-design/icons-vue'
import type { TranslationJob, FileUpload, LanguagePair, DocumentType, OutputMode } from '@/types'
import { DocumentType as DocType } from '@/types'

// Lazy load heavy components
const FileUploader = defineAsyncComponent(() => import('@/components/FileUploader.vue'))
const LanguagePairSelector = defineAsyncComponent(() => import('@/components/LanguagePairSelector.vue'))
const ProgressTracker = defineAsyncComponent(() => import('@/components/ProgressTracker.vue'))
const CatalogSelector = defineAsyncComponent(() => import('@/components/CatalogSelector.vue'))

// Stores
const jobStore = useJobStore()

// Composables
const errorHandler = useErrorHandler({ showNotification: true })
const loading = useLoading(['createJob'])
const fileDownload = useFileDownload()
const { t } = useLanguage()

// GraphQL mutation
const { mutate: createTranslationJob } = useMutation<{
  createTranslationJob: TranslationJob
}>(CREATE_TRANSLATION_JOB_MUTATION)

// Component refs
const fileUploaderRef = ref<InstanceType<typeof FileUploader> | null>(null)
const languagePairSelectorRef = ref<InstanceType<typeof LanguagePairSelector> | null>(null)

// State
const uploadedFiles = ref<FileUpload[]>([])
const selectedLanguagePairId = ref<string>('')
const selectedLanguagePair = ref<LanguagePair | null>(null)
const selectedCatalogIds = ref<string[]>([])
const outputMode = ref<OutputMode>('replace')

// Computed properties for GraphQL mutation
const autoAppend = computed(() => outputMode.value === 'append')
const interleavedMode = computed(() => outputMode.value === 'interleaved')

// Computed
const currentJob = computed(() => jobStore.currentJob)
const completedJobs = computed(() => jobStore.completedJobs)
const isCreatingJob = computed(() => loading.isKeyLoading('createJob'))

const canStartJob = computed(() => {
  return uploadedFiles.value.length > 0 && selectedLanguagePairId.value !== ''
})

const validationMessage = computed(() => {
  if (uploadedFiles.value.length === 0) {
    return t('translation.validationUpload', 'Please upload at least one document')
  }
  if (!selectedLanguagePairId.value) {
    return t('translation.validationLanguage', 'Please select a language pair')
  }
  return ''
})

// Lifecycle
onMounted(async () => {
  // Fetch job history from backend API
  try {
    await jobStore.fetchJobHistory()
  } catch (error) {
    console.error('Failed to load job history:', error)
    // Error is logged but not shown to user since it's non-critical
  }
})

// Event handlers
function handleFilesChanged(files: FileUpload[]) {
  uploadedFiles.value = files
}

function handleUploadError(error: string) {
  errorHandler.handleError(error, 'File Upload')
}

function handleLanguagePairChange(pair: LanguagePair | null) {
  selectedLanguagePair.value = pair
}

function handleLanguagePairError(error: string) {
  errorHandler.handleError(error, 'Language Pair Selection')
}

async function handleStartTranslation() {
  // Validate
  if (!canStartJob.value) {
    errorHandler.handleError(validationMessage.value, 'Validation')
    return
  }

  // Validate components
  if (languagePairSelectorRef.value && !languagePairSelectorRef.value.validate()) {
    return
  }

  try {
    await loading.withLoading(async () => {
      // Create translation job
      const fileIds = uploadedFiles.value.map((f) => f.id)
      const result = await createTranslationJob({
        fileIds,
        languagePairId: selectedLanguagePairId.value,
        catalogIds: selectedCatalogIds.value.length > 0 ? selectedCatalogIds.value : undefined,
        autoAppend: autoAppend.value,
        interleavedMode: interleavedMode.value,
      })

      if (result?.data?.createTranslationJob) {
        const job = result.data.createTranslationJob
        
        // Store job in job store
        jobStore.addJob(job)
        jobStore.setCurrentJob(job)

        // Clear uploaded files and catalog selection
        if (fileUploaderRef.value) {
          fileUploaderRef.value.clearFiles()
        }
        uploadedFiles.value = []
        selectedCatalogIds.value = []

        // Show success message
        errorHandler.showSuccess(
          'Translation Job Started',
          `Job ${job.id} has been created and is now processing`
        )
      }
    }, 'createJob')
  } catch (error) {
    errorHandler.handleError(error, 'Create Translation Job')
  }
}

function handleJobComplete(job: TranslationJob) {
  // Update job in store
  jobStore.updateJob(job)

  // Show completion notification
  if (job.status === 'COMPLETED') {
    errorHandler.showSuccess(
      'Translation Complete',
      `Job ${job.id} completed successfully. ${job.filesCompleted} files translated.`
    )
  } else if (job.status === 'PARTIAL_SUCCESS') {
    errorHandler.showWarning(
      'Translation Partially Complete',
      `Job ${job.id} completed with some errors. ${job.filesCompleted} files succeeded, ${job.filesFailed.length} failed.`
    )
  } else if (job.status === 'FAILED') {
    errorHandler.handleError(
      `Job ${job.id} failed. Please check the error details.`,
      'Translation Job'
    )
  }

  // Clear current job if it's the one that completed
  if (currentJob.value?.id === job.id) {
    jobStore.clearCurrentJob()
  }
}

function handleProgressError(error: Error) {
  errorHandler.handleError(error, 'Progress Tracking')
}

async function handleDownload(jobId: string, filename: string) {
  try {
    await fileDownload.downloadFile(jobId, filename)
  } catch (error) {
    // Error is already handled by useFileDownload
    console.error('Download failed:', error)
  }
}

// Helper functions
function getCompletedFiles(job: TranslationJob): Array<{ filename: string }> {
  // Return the actual completed files from the job
  if (!job.completedFiles || !Array.isArray(job.completedFiles)) {
    return []
  }
  return job.completedFiles.map(cf => ({ filename: cf.outputFilename }))
}

function getStatusColor(status: string): string {
  switch (status) {
    case 'COMPLETED':
      return 'success'
    case 'FAILED':
      return 'error'
    case 'PARTIAL_SUCCESS':
      return 'warning'
    case 'PROCESSING':
      return 'processing'
    default:
      return 'default'
  }
}

function formatDate(dateString?: string): string {
  if (!dateString) return 'N/A'
  return new Date(dateString).toLocaleDateString(undefined, {
      month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
  })
}

// Get document type from filename
function getDocumentTypeFromFilename(filename: string): DocumentType | undefined {
  const ext = filename.toLowerCase().split('.').pop()
  switch (ext) {
    case 'xlsx':
      return DocType.EXCEL
    case 'docx':
      return DocType.WORD
    case 'pptx':
      return DocType.POWERPOINT
    case 'pdf':
      return DocType.PDF
    default:
      return undefined
  }
}

// Get icon color for document type
function getDocumentIconColor(documentType?: DocumentType): string {
  switch (documentType) {
    case DocType.EXCEL:
      return '#10b981' // Emerald/Green
    case DocType.WORD:
      return '#1890ff' // Blue
    case DocType.POWERPOINT:
      return '#fa541c' // Orange
    case DocType.PDF:
      return '#f5222d' // Red
    default:
      return '#8c8c8c' // Gray
  }
}
</script>

<style scoped>
.main-page {
  min-height: calc(100vh - 64px);
  background: transparent;
}

.content {
  padding: 32px 24px;
  max-width: 1400px;
  margin: 0 auto;
  width: 100%;
}

.page-header {
  margin-bottom: 32px;
  text-align: left;
}

.page-header h1 {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-main);
  margin-bottom: 8px;
  letter-spacing: -0.5px;
}

.subtitle {
  color: var(--text-secondary);
  font-size: 16px;
}

.section-card {
  height: 100%;
  border: none;
  overflow: hidden;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 18px;
  font-weight: 600;
  color: var(--text-main);
}

.header-icon {
  color: var(--primary-color);
  font-size: 20px;
}

.optional-badge {
  font-size: 12px;
  font-weight: 400;
  color: var(--text-secondary);
  background: var(--item-hover-bg);
  padding: 2px 8px;
  border-radius: 4px;
  margin-left: auto;
}

/* Job Controls */
.job-controls {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 8px 0;
}

.action-description {
  color: var(--text-secondary);
  font-size: 14px;
}

.output-mode-selector {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: var(--glass-card-bg);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  flex-wrap: wrap;
}

.output-mode-selector .selector-label {
  font-size: 14px;
  color: var(--text-main);
  font-weight: 500;
}

.output-mode-selector .help-icon {
  color: var(--text-secondary);
  font-size: 14px;
  cursor: help;
  margin-right: 8px;
}

.output-mode-radio-group {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.start-button {
  height: 48px;
  font-size: 16px;
  font-weight: 600;
  border-radius: 12px;
  background: linear-gradient(135deg, var(--primary-color), var(--primary-hover));
  border: none;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
  transition: all 0.3s;
}

.start-button:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(99, 102, 241, 0.4);
}

.info-alert {
  background-color: var(--glass-card-bg);
  border: 1px solid var(--border-color);
  border-radius: 8px;
}

/* History/Job List */
.empty-state {
  padding: 60px 0;
  opacity: 0.6;
}

.job-list {
  margin-top: 16px;
}

.job-item {
  background: var(--glass-card-bg);
  border-radius: 12px;
  border: 1px solid var(--border-color);
  margin-bottom: 16px;
  padding: 16px;
  transition: all 0.3s;
}

.job-item:hover {
  background: var(--surface-color);
  box-shadow: var(--shadow-md);
}

.job-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 12px;
}

.job-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-tag {
  border-radius: 4px;
  font-weight: 600;
  border: none;
}

.job-id {
  font-family: monospace;
  color: var(--text-secondary);
  font-size: 14px;
  background: rgba(0,0,0,0.03);
  padding: 2px 6px;
  border-radius: 4px;
}

.job-date {
  color: var(--text-secondary);
  font-size: 13px;
}

.job-stats {
  color: var(--text-secondary);
  font-size: 13px;
}

/* File Download Grid */
.download-section {
  padding-top: 12px;
  border-top: 1px solid rgba(0,0,0,0.05);
}

.files-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
}

.file-download-card {
  display: flex;
  align-items: center;
  padding: 10px;
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  gap: 10px;
  transition: all 0.2s;
}

.file-download-card:hover {
  border-color: var(--primary-color);
  transform: translateY(-1px);
}

.doc-icon {
  font-size: 24px;
}

.file-info {
  flex: 1;
  min-width: 0;
}

.filename {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-main);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 4px;
}

.download-btn {
  color: var(--primary-color);
  padding: 0;
  font-size: 12px;
}

.download-btn:hover {
  color: var(--primary-hover);
  background: transparent;
}

/* Failed Files */
.failed-files-section {
  margin-top: 16px;
  background: #fef2f2;
  border-radius: 8px;
  padding: 12px;
  border: 1px solid #fee2e2;
}

.failed-header {
  font-weight: 600;
  color: #ef4444;
  margin-bottom: 8px;
  font-size: 13px;
}

.failed-file {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #b91c1c;
}

.error-icon {
  color: #ef4444;
}

/* Responsive */
@media (max-width: 768px) {
  .content {
    padding: 16px;
  }
  
  .job-header {
    flex-direction: column;
  }
  
  .files-grid {
    grid-template-columns: 1fr;
  }
}

/* Disabled card state */
.disabled-card {
  opacity: 0.7;
}

.disabled-card .card-header {
  color: var(--text-secondary);
}

.placeholder-content {
  padding: 40px 0;
  text-align: center;
}

.placeholder-content .ant-empty-description {
  color: var(--text-secondary);
  font-size: 14px;
}
</style>
