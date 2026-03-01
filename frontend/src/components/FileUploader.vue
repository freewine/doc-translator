<template>
  <div class="file-uploader">
    <div
      class="upload-area"
      :class="{ 'drag-over': isDragOver, 'disabled': uploading }"
      @drop.prevent="handleDrop"
      @dragover.prevent="handleDragOver"
      @dragleave.prevent="handleDragLeave"
      @click="triggerFileInput"
    >
      <input
        ref="fileInput"
        type="file"
        multiple
        accept=".xlsx,.docx,.pptx,.pdf,.txt,.md"
        style="display: none"
        @change="handleFileSelect"
        :disabled="uploading"
      />
      <div class="upload-icon">
        <CloudUploadOutlined style="font-size: 48px; color: #1890ff" />
      </div>
      <div class="upload-text">
        <p class="primary-text">
          {{ uploading ? t('fileUpload.uploading') : t('fileUpload.dragDrop') }}
        </p>
        <p class="secondary-text">{{ t('fileUpload.invalidFormat') }}</p>
      </div>
    </div>

    <div v-if="files.length > 0" class="file-list">
      <h3>{{ t('fileUpload.selectedFiles') }} ({{ files.length }})</h3>
      <a-list :data-source="files" :loading="uploading">
        <template #renderItem="{ item }">
          <a-list-item>
            <a-list-item-meta>
              <template #title>
                <div class="file-info">
                  <component 
                    :is="getDocumentIconComponent(item.documentType || getDocumentType(item.filename))" 
                    :style="{ color: getDocumentIconColor(item.documentType || getDocumentType(item.filename)), marginRight: '8px' }" 
                  />
                  <span class="file-name">{{ item.filename }}</span>
                </div>
              </template>
              <template #description>
                <span class="file-size">{{ formatFileSize(item.size) }}</span>
              </template>
            </a-list-item-meta>
            <template #actions>
              <a-button
                type="link"
                danger
                @click="removeFile(item.id)"
                :disabled="uploading"
              >
                <DeleteOutlined />
                {{ t('fileUpload.remove') }}
              </a-button>
            </template>
          </a-list-item>
        </template>
      </a-list>
    </div>

    <div v-if="errorMessage" class="error-message">
      <a-alert
        :message="errorMessage"
        type="error"
        closable
        @close="errorMessage = ''"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, markRaw, type Component } from 'vue'
import { CloudUploadOutlined, DeleteOutlined, FileExcelOutlined, FileWordOutlined, FilePptOutlined, FilePdfOutlined, FileTextOutlined, FileOutlined } from '@ant-design/icons-vue'
import { useErrorHandler } from '@/composables/useErrorHandler'
import { useLoading } from '@/composables/useLoading'
import { useLanguage } from '@/composables/useLanguage'
import type { FileUpload, DocumentType } from '@/types'
import { DocumentType as DocType } from '@/types'

// Props
interface Props {
  maxFiles?: number
}

const props = withDefaults(defineProps<Props>(), {
  maxFiles: 100
})

// Emits
const emit = defineEmits<{
  filesChanged: [files: FileUpload[]]
  uploadError: [error: string]
}>()

// State
const fileInput = ref<HTMLInputElement | null>(null)
const files = ref<FileUpload[]>([])
const isDragOver = ref(false)
const errorMessage = ref('')

// Error handling and loading
const errorHandler = useErrorHandler({ showNotification: true })
const loading = useLoading(['upload'])
const uploading = computed(() => loading.isKeyLoading('upload'))
const { t } = useLanguage()

// Supported file extensions
const SUPPORTED_EXTENSIONS = ['.xlsx', '.docx', '.pptx', '.pdf', '.txt', '.md']

// Get document type from file extension
function getDocumentType(filename: string): DocumentType | undefined {
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
    case 'txt':
      return DocType.TEXT
    case 'md':
      return DocType.MARKDOWN
    default:
      return undefined
  }
}

// Get icon component for document type
function getDocumentIconComponent(documentType?: DocumentType): Component {
  switch (documentType) {
    case DocType.EXCEL:
      return markRaw(FileExcelOutlined)
    case DocType.WORD:
      return markRaw(FileWordOutlined)
    case DocType.POWERPOINT:
      return markRaw(FilePptOutlined)
    case DocType.PDF:
      return markRaw(FilePdfOutlined)
    case DocType.TEXT:
    case DocType.MARKDOWN:
      return markRaw(FileTextOutlined)
    default:
      return markRaw(FileOutlined)
  }
}

// Get icon type for document
function getDocumentIcon(documentType?: DocumentType): string {
  switch (documentType) {
    case DocType.EXCEL:
      return 'file-excel'
    case DocType.WORD:
      return 'file-word'
    case DocType.POWERPOINT:
      return 'file-ppt'
    case DocType.PDF:
      return 'file-pdf'
    default:
      return 'file'
  }
}

// Get icon color for document
function getDocumentIconColor(documentType?: DocumentType): string {
  switch (documentType) {
    case DocType.EXCEL:
      return '#52c41a' // Green
    case DocType.WORD:
      return '#1890ff' // Blue
    case DocType.POWERPOINT:
      return '#fa541c' // Orange
    case DocType.PDF:
      return '#f5222d' // Red
    case DocType.TEXT:
      return '#595959' // Dark gray
    case DocType.MARKDOWN:
      return '#722ed1' // Purple
    default:
      return '#8c8c8c' // Gray
  }
}

// Check if file has supported extension
function isSupportedFile(filename: string): boolean {
  const ext = '.' + filename.toLowerCase().split('.').pop()
  return SUPPORTED_EXTENSIONS.includes(ext)
}

// Methods
function triggerFileInput() {
  if (!uploading.value && fileInput.value) {
    fileInput.value.click()
  }
}

function handleDragOver(event: DragEvent) {
  if (!uploading.value) {
    isDragOver.value = true
  }
}

function handleDragLeave(event: DragEvent) {
  isDragOver.value = false
}

async function handleDrop(event: DragEvent) {
  isDragOver.value = false
  
  if (uploading.value) {
    return
  }

  const droppedFiles = event.dataTransfer?.files
  if (droppedFiles) {
    await processFiles(Array.from(droppedFiles))
  }
}

async function handleFileSelect(event: Event) {
  const target = event.target as HTMLInputElement
  const selectedFiles = target.files
  
  if (selectedFiles) {
    await processFiles(Array.from(selectedFiles))
    // Reset input so the same file can be selected again
    target.value = ''
  }
}

async function processFiles(fileList: File[]) {
  // Validate file extensions
  const invalidFiles = fileList.filter(file => !isSupportedFile(file.name))
  
  if (invalidFiles.length > 0) {
    const message = `Invalid file type(s): ${invalidFiles.map(f => f.name).join(', ')}. Supported formats: ${SUPPORTED_EXTENSIONS.join(', ')}`
    errorMessage.value = message
    errorHandler.handleError(message, 'File Validation')
    emit('uploadError', message)
    return
  }

  // Check max files limit
  if (files.value.length + fileList.length > props.maxFiles) {
    const message = `Cannot upload more than ${props.maxFiles} files. Current: ${files.value.length}, Attempting to add: ${fileList.length}`
    errorMessage.value = message
    errorHandler.handleError(message, 'File Limit')
    emit('uploadError', message)
    return
  }

  // Upload files
  errorMessage.value = ''
  errorHandler.clearError()

  try {
    await loading.withLoading(async () => {
      let successCount = 0
      let failCount = 0

      for (const file of fileList) {
        try {
          // Use REST API for file upload instead of GraphQL
          const formData = new FormData()
          formData.append('file', file)
          
          const token = localStorage.getItem('auth_token')
          const response = await fetch(import.meta.env.VITE_API_URL?.replace('/graphql', '/upload') || 'http://localhost:8000/api/upload', {
            method: 'POST',
            headers: {
              'Authorization': token ? `Bearer ${token}` : '',
            },
            body: formData
          })

          if (!response.ok) {
            const error = await response.json()
            throw new Error(error.error || 'Upload failed')
          }

          const result = await response.json()
          files.value.push(result)
          successCount++
        } catch (error: any) {
          failCount++
          const message = `Failed to upload ${file.name}`
          errorMessage.value = message
          errorHandler.handleError(error, `Uploading ${file.name}`)
          emit('uploadError', message)
        }
      }

      // Show success message if any files uploaded
      if (successCount > 0) {
        errorHandler.showSuccess(
          t('fileUpload.uploadComplete', 'Upload Complete'),
          t('fileUpload.uploadSuccess', { count: successCount, failed: failCount > 0 ? `, ${failCount} ${t('fileUpload.failed', 'failed')}` : '' })
        )
      }

      // Emit updated file list
      emit('filesChanged', files.value)
    }, 'upload')
  } catch (error) {
    errorHandler.handleError(error, 'File Upload')
  }
}

function removeFile(fileId: string) {
  files.value = files.value.filter(f => f.id !== fileId)
  emit('filesChanged', files.value)
}

function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes'
  
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
}

// Expose methods for parent component
defineExpose({
  clearFiles: () => {
    files.value = []
    emit('filesChanged', files.value)
  },
  getFiles: () => files.value
})
</script>

<style scoped>
.file-uploader {
  width: 100%;
}

.upload-area {
  border: 2px dashed var(--border-color);
  border-radius: 8px;
  padding: 40px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  background-color: var(--surface-color);
}

.upload-area:hover:not(.disabled) {
  border-color: var(--primary-color);
  background-color: var(--glass-card-bg);
}

.upload-area.drag-over {
  border-color: var(--primary-color);
  background-color: var(--glass-card-bg);
  transform: scale(1.02);
}

.upload-area.disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.upload-icon {
  margin-bottom: 16px;
}

.upload-text .primary-text {
  font-size: 16px;
  color: var(--text-main);
  margin-bottom: 8px;
}

.upload-text .secondary-text {
  font-size: 14px;
  color: var(--text-secondary);
  margin: 0;
}

.file-list {
  margin-top: 24px;
}

.file-list h3 {
  margin-bottom: 16px;
  font-size: 16px;
  font-weight: 600;
}

.file-info {
  display: flex;
  align-items: center;
}

.file-name {
  font-weight: 500;
}

.file-size {
  color: #8c8c8c;
  font-size: 12px;
}

.error-message {
  margin-top: 16px;
}

/* Mobile layout (< 768px) */
@media (max-width: 767px) {
  .upload-area {
    padding: 20px 16px;
  }

  .upload-icon {
    margin-bottom: 12px;
  }

  .upload-icon :deep(svg) {
    font-size: 36px !important;
  }

  .upload-text .primary-text {
    font-size: 14px;
    margin-bottom: 6px;
  }

  .upload-text .secondary-text {
    font-size: 12px;
  }

  .file-list h3 {
    font-size: 15px;
    margin-bottom: 12px;
  }

  .file-name {
    font-size: 13px;
  }

  .file-size {
    font-size: 11px;
  }

  :deep(.ant-list-item) {
    padding: 12px 0;
  }

  :deep(.ant-list-item-action) {
    margin-left: 8px;
  }
}

/* Tablet layout (768px - 1024px) */
@media (min-width: 768px) and (max-width: 1024px) {
  .upload-area {
    padding: 32px;
  }

  .upload-icon :deep(svg) {
    font-size: 42px !important;
  }

  .upload-text .primary-text {
    font-size: 15px;
  }

  .upload-text .secondary-text {
    font-size: 13px;
  }
}

/* Desktop layout (> 1024px) */
@media (min-width: 1025px) {
  .upload-area {
    padding: 40px;
  }

  .upload-icon :deep(svg) {
    font-size: 48px !important;
  }
}

/* Small mobile devices */
@media (max-width: 480px) {
  .upload-area {
    padding: 16px 12px;
  }

  .upload-icon {
    margin-bottom: 10px;
  }

  .upload-icon :deep(svg) {
    font-size: 32px !important;
  }

  .upload-text .primary-text {
    font-size: 13px;
  }

  .upload-text .secondary-text {
    font-size: 11px;
  }

  .file-list h3 {
    font-size: 14px;
  }

  :deep(.ant-list-item-meta-title) {
    font-size: 13px;
  }

  :deep(.ant-btn) {
    font-size: 13px;
    padding: 4px 8px;
  }
}
</style>
