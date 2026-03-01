<template>
  <a-modal
    :open="visible"
    :title="t('thesaurus.importTerms', 'Import Terms from CSV')"
    :footer="null"
    width="600px"
    @cancel="handleClose"
  >
    <div class="import-dialog">
      <!-- Step 1: File Upload -->
      <div v-if="!importResult" class="upload-section">
        <a-upload-dragger
          v-model:file-list="fileList"
          name="file"
          :multiple="false"
          :before-upload="handleBeforeUpload"
          :accept="'.csv'"
          :show-upload-list="false"
        >
          <p class="ant-upload-drag-icon">
            <InboxOutlined />
          </p>
          <p class="ant-upload-text">{{ t('thesaurus.dragCsvHere', 'Click or drag CSV file to this area') }}</p>
          <p class="ant-upload-hint">
            {{ t('thesaurus.csvFormat', 'CSV must have columns: source_term, target_term') }}
          </p>
        </a-upload-dragger>

        <!-- Preview -->
        <div v-if="previewData.length > 0" class="preview-section">
          <h4>{{ t('thesaurus.preview', 'Preview') }} ({{ previewData.length }} {{ t('thesaurus.rows', 'rows') }})</h4>
          <a-table
            :columns="previewColumns"
            :data-source="previewData.slice(0, 5)"
            :pagination="false"
            size="small"
            :row-key="(_record: { sourceTerm: string; targetTerm: string }, index: number) => index"
          />
          <p v-if="previewData.length > 5" class="preview-note">
            ...and {{ previewData.length - 5 }} more rows
          </p>
        </div>

        <!-- Parse Errors -->
        <div v-if="parseErrors.length > 0" class="error-section">
          <a-alert
            type="warning"
            :message="t('thesaurus.parseWarnings', 'Some rows have issues')"
            show-icon
          >
            <template #description>
              <ul class="error-list">
                <li v-for="(error, index) in parseErrors.slice(0, 5)" :key="index">
                  {{ error }}
                </li>
                <li v-if="parseErrors.length > 5">
                  ...and {{ parseErrors.length - 5 }} more issues
                </li>
              </ul>
            </template>
          </a-alert>
        </div>

        <!-- Actions -->
        <div class="actions">
          <a-button @click="handleClose">{{ t('common.cancel') }}</a-button>
          <a-button
            type="primary"
            :disabled="previewData.length === 0"
            :loading="isImporting"
            @click="handleImport"
          >
            <UploadOutlined />
            {{ t('thesaurus.importNow', 'Import Now') }}
          </a-button>
        </div>
      </div>

      <!-- Step 2: Import Results -->
      <div v-else class="result-section">
        <a-result
          :status="importResult.skipped > 0 ? 'warning' : 'success'"
          :title="t('thesaurus.importComplete', 'Import Complete')"
        >
          <template #subTitle>
            <div class="result-stats">
              <div class="stat-item success">
                <CheckCircleOutlined />
                <span>{{ importResult.created }} {{ t('thesaurus.created', 'created') }}</span>
              </div>
              <div class="stat-item info">
                <SyncOutlined />
                <span>{{ importResult.updated }} {{ t('thesaurus.updated', 'updated') }}</span>
              </div>
              <div v-if="importResult.skipped > 0" class="stat-item warning">
                <ExclamationCircleOutlined />
                <span>{{ importResult.skipped }} {{ t('thesaurus.skipped', 'skipped') }}</span>
              </div>
            </div>
          </template>

          <!-- Import Errors -->
          <template v-if="importResult.errors.length > 0" #extra>
            <a-collapse>
              <a-collapse-panel :header="t('thesaurus.viewErrors', 'View Errors')">
                <ul class="error-list">
                  <li v-for="(error, index) in importResult.errors.slice(0, 10)" :key="index">
                    {{ error }}
                  </li>
                  <li v-if="importResult.errors.length > 10">
                    ...and {{ importResult.errors.length - 10 }} more
                  </li>
                </ul>
              </a-collapse-panel>
            </a-collapse>
          </template>
        </a-result>

        <div class="actions">
          <a-button type="primary" @click="handleDone">
            {{ t('common.ok') }}
          </a-button>
        </div>
      </div>
    </div>
  </a-modal>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { UploadFile } from 'ant-design-vue'
import { useThesaurusStore } from '@/stores/thesaurus'
import { useErrorHandler } from '@/composables/useErrorHandler'
import { useLanguage } from '@/composables/useLanguage'
import type { ImportResult } from '@/types'
import {
  InboxOutlined,
  UploadOutlined,
  CheckCircleOutlined,
  SyncOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons-vue'

// Props
interface Props {
  visible: boolean
  languagePairId: string
  catalogId: string
}

const props = defineProps<Props>()

// Emits
const emit = defineEmits<{
  'update:visible': [value: boolean]
  'imported': []
}>()

// Stores
const thesaurusStore = useThesaurusStore()

// Composables
const errorHandler = useErrorHandler({ showNotification: true })
const { t } = useLanguage()

// State
const fileList = ref<UploadFile[]>([])
const csvContent = ref('')
const previewData = ref<Array<{ sourceTerm: string; targetTerm: string }>>([])
const parseErrors = ref<string[]>([])
const isImporting = ref(false)
const importResult = ref<ImportResult | null>(null)

// Computed
const previewColumns = computed(() => [
  {
    title: t('thesaurus.sourceTerm', 'Source Term'),
    dataIndex: 'sourceTerm',
    key: 'sourceTerm',
  },
  {
    title: t('thesaurus.targetTerm', 'Target Term'),
    dataIndex: 'targetTerm',
    key: 'targetTerm',
  },
])

// Methods
function handleClose() {
  emit('update:visible', false)
  resetState()
}

function handleDone() {
  emit('imported')
  handleClose()
}

function resetState() {
  fileList.value = []
  csvContent.value = ''
  previewData.value = []
  parseErrors.value = []
  importResult.value = null
}

function handleBeforeUpload(file: File): boolean {
  // Read file content
  const reader = new FileReader()
  reader.onload = (e) => {
    const content = e.target?.result as string
    csvContent.value = content
    parseCSV(content)
  }
  reader.onerror = () => {
    errorHandler.handleError('Failed to read file', 'File Read')
  }
  reader.readAsText(file)
  
  // Prevent auto upload
  return false
}

function parseCSV(content: string) {
  previewData.value = []
  parseErrors.value = []
  
  const lines = content.split(/\r?\n/).filter(line => line.trim())
  
  if (lines.length === 0) {
    parseErrors.value.push(t('thesaurus.emptyFile', 'File is empty'))
    return
  }
  
  // Check header
  const header = lines[0]?.toLowerCase() || ''
  const hasHeader = header.includes('source') || header.includes('target')
  const startIndex = hasHeader ? 1 : 0
  
  for (let i = startIndex; i < lines.length; i++) {
    const line = lines[i]
    if (!line?.trim()) continue
    
    // Parse CSV line (handle quoted values)
    const values = parseCSVLine(line)
    
    if (values.length < 2) {
      parseErrors.value.push(`Row ${i + 1}: ${t('thesaurus.insufficientColumns', 'Insufficient columns')}`)
      continue
    }
    
    const sourceTerm = values[0]?.trim() || ''
    const targetTerm = values[1]?.trim() || ''
    
    if (!sourceTerm || !targetTerm) {
      parseErrors.value.push(`Row ${i + 1}: ${t('thesaurus.emptyTerms', 'Empty source or target term')}`)
      continue
    }
    
    previewData.value.push({ sourceTerm, targetTerm })
  }
}

function parseCSVLine(line: string): string[] {
  const result: string[] = []
  let current = ''
  let inQuotes = false
  
  for (let i = 0; i < line.length; i++) {
    const char = line[i]
    
    if (char === '"') {
      if (inQuotes && line[i + 1] === '"') {
        current += '"'
        i++
      } else {
        inQuotes = !inQuotes
      }
    } else if (char === ',' && !inQuotes) {
      result.push(current)
      current = ''
    } else {
      current += char
    }
  }
  
  result.push(current)
  return result
}

async function handleImport() {
  if (!props.languagePairId || !props.catalogId || !csvContent.value) {
    return
  }
  
  isImporting.value = true
  try {
    const result = await thesaurusStore.importFromCsv(
      props.languagePairId,
      props.catalogId,
      csvContent.value
    )
    importResult.value = result
  } catch (err) {
    errorHandler.handleError(err, 'Import CSV')
  } finally {
    isImporting.value = false
  }
}
</script>

<style scoped>
.import-dialog {
  padding: 8px 0;
}

.preview-section {
  margin-top: 24px;
}

.preview-section h4 {
  margin-bottom: 12px;
  font-weight: 600;
  color: var(--text-main);
}

.preview-note {
  margin-top: 8px;
  color: var(--text-secondary);
  font-size: 13px;
}

.error-section {
  margin-top: 16px;
}

.error-list {
  margin: 0;
  padding-left: 20px;
  font-size: 13px;
}

.error-list li {
  margin-bottom: 4px;
}

.actions {
  margin-top: 24px;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.result-section {
  text-align: center;
}

.result-stats {
  display: flex;
  justify-content: center;
  gap: 24px;
  margin-top: 16px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
}

.stat-item.success {
  color: var(--success-color, #52c41a);
}

.stat-item.info {
  color: var(--primary-color);
}

.stat-item.warning {
  color: var(--warning-color, #faad14);
}
</style>
