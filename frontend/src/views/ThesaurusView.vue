<template>
  <div class="thesaurus-page">
    <div class="content">
      <div class="page-header">
        <h1>{{ t('thesaurus.title', 'Term Thesaurus') }}</h1>
        <p class="subtitle">{{ t('thesaurus.subtitle', 'Manage translation term pairs for consistent terminology.') }}</p>
      </div>

      <a-row :gutter="[24, 24]">
        <!-- Language Pair and Catalog Selection -->
        <a-col :xs="24" :sm="24" :md="12" :lg="8" :xl="6">
          <a-card :bordered="false" class="section-card glass-card sticky-card">
            <template #title>
              <div class="card-header">
                <GlobalOutlined class="header-icon" />
                <span>{{ t('thesaurus.languageAndCatalog', 'Language & Catalog') }}</span>
              </div>
            </template>
            
            <a-form layout="vertical">
              <a-form-item style="margin-bottom: 24px;">
                <template #label>
                  <span class="form-section-title">{{ t('languagePair.title') }}</span>
                </template>
                <a-select
                  v-model:value="selectedLanguagePairId"
                  :placeholder="t('languagePair.select')"
                  :loading="configStore.isLoading"
                  size="middle"
                  @change="handleLanguagePairChange"
                  style="width: 100%"
                >
                  <a-select-option
                    v-for="pair in languagePairs"
                    :key="pair.id"
                    :value="pair.id"
                  >
                    {{ pair.sourceLanguage }} → {{ pair.targetLanguage }}
                  </a-select-option>
                </a-select>
              </a-form-item>

              <CatalogManager
                v-if="selectedLanguagePairId"
                :language-pair-id="selectedLanguagePairId"
                :selected-catalog-id="selectedCatalogId"
                @select="handleCatalogSelect"
                @catalog-created="handleCatalogCreated"
                @catalog-deleted="handleCatalogDeleted"
              />
              <div v-else class="empty-state" style="padding: 20px 0;">
                <a-empty :description="t('thesaurus.selectLanguagePairFirst', 'Select a language pair first')" :image="false" />
              </div>
            </a-form>
          </a-card>
        </a-col>

        <!-- Term List -->
        <a-col :xs="24" :sm="24" :md="12" :lg="16" :xl="18">
          <a-card :bordered="false" class="section-card glass-card">
            <template #title>
              <div class="card-header">
                <BookOutlined class="header-icon" />
                <span>{{ t('thesaurus.termPairs', 'Term Pairs') }}</span>
                <span v-if="thesaurusStore.totalItems > 0" class="term-count">
                  ({{ thesaurusStore.totalItems }})
                </span>
              </div>
            </template>
            <template #extra>
              <a-space>
                <a-input-search
                  v-model:value="searchText"
                  :placeholder="t('thesaurus.searchPlaceholder', 'Search source terms...')"
                  style="width: 200px"
                  @search="handleSearch"
                  @change="handleSearchChange"
                  allow-clear
                />
                <a-button
                  type="primary"
                  :disabled="!selectedCatalogId"
                  @click="showAddTermDialog"
                  v-if="canEdit"
                >
                  <PlusOutlined />
                  {{ t('thesaurus.addTerm', 'Add Term') }}
                </a-button>
                <a-dropdown :trigger="['click']">
                  <a-button>
                    <MoreOutlined />
                  </a-button>
                  <template #overlay>
                    <a-menu>
                      <a-menu-item v-if="canEdit" key="import" :disabled="!selectedCatalogId" @click="showImportDialog = true">
                        <UploadOutlined />
                        {{ t('thesaurus.import', 'Import CSV') }}
                      </a-menu-item>
                      <a-menu-item key="export" :disabled="!selectedCatalogId || thesaurusStore.totalItems === 0" @click="handleExport">
                        <DownloadOutlined />
                        {{ t('thesaurus.export', 'Export CSV') }}
                      </a-menu-item>
                    </a-menu>
                  </template>
                </a-dropdown>
              </a-space>
            </template>

            <div v-if="!selectedLanguagePairId" class="empty-state">
              <a-empty :description="t('thesaurus.selectLanguagePairFirst', 'Please select a language pair first')" />
            </div>
            <div v-else-if="!selectedCatalogId" class="empty-state">
              <a-empty :description="t('thesaurus.selectCatalogFirst', 'Please select or create a catalog')" />
            </div>
            <div v-else>
              <a-table
                :columns="columns"
                :data-source="thesaurusStore.termPairs"
                :loading="thesaurusStore.isLoading"
                :pagination="pagination"
                :row-key="(record: TermPair) => record.id"
                @change="handleTableChange"
                :scroll="{ x: 600 }"
              >
                <template #bodyCell="{ column, record }">
                  <template v-if="column.key === 'sourceTerm'">
                    <span class="source-term">{{ record.sourceTerm }}</span>
                  </template>
                  <template v-else-if="column.key === 'targetTerm'">
                    <span class="target-term">{{ record.targetTerm }}</span>
                  </template>
                  <template v-else-if="column.key === 'updatedAt'">
                    <span class="date-text">{{ formatDate(record.updatedAt) }}</span>
                  </template>
                  <template v-else-if="column.key === 'actions'">
                    <a-space>
                      <a-button type="text" size="small" @click="showEditTermDialog(record)">
                        <EditOutlined />
                      </a-button>
                      <a-popconfirm
                        :title="t('thesaurus.confirmDelete', 'Delete this term pair?')"
                        @confirm="handleDeleteTerm(record.id)"
                      >
                        <a-button type="text" size="small" danger>
                          <DeleteOutlined />
                        </a-button>
                      </a-popconfirm>
                    </a-space>
                  </template>
                </template>
              </a-table>
            </div>
          </a-card>
        </a-col>
      </a-row>
    </div>

    <!-- Term Edit Dialog -->
    <TermEditDialog
      v-model:visible="showTermDialog"
      :term="editingTerm"
      :language-pair-id="selectedLanguagePairId"
      :catalog-id="selectedCatalogId"
      @saved="handleTermSaved"
    />

    <!-- Import Dialog -->
    <TermImportDialog
      v-model:visible="showImportDialog"
      :language-pair-id="selectedLanguagePairId"
      :catalog-id="selectedCatalogId"
      @imported="handleImportComplete"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, defineAsyncComponent } from 'vue'
import { useThesaurusStore } from '@/stores/thesaurus'
import { useConfigStore } from '@/stores/config'
import { useAuthStore } from '@/stores/auth'
import { useErrorHandler } from '@/composables/useErrorHandler'
import { useLanguage } from '@/composables/useLanguage'
import { triggerBlobDownload } from '@/utils/download'
import type { TermPair } from '@/types'
import type { TablePaginationConfig } from 'ant-design-vue'
import {
  GlobalOutlined,
  BookOutlined,
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  UploadOutlined,
  DownloadOutlined,
  MoreOutlined,
} from '@ant-design/icons-vue'

// Lazy load dialog components
const CatalogManager = defineAsyncComponent(() => import('@/components/CatalogManager.vue'))
const TermEditDialog = defineAsyncComponent(() => import('@/components/TermEditDialog.vue'))
const TermImportDialog = defineAsyncComponent(() => import('@/components/TermImportDialog.vue'))

// Stores
const thesaurusStore = useThesaurusStore()
const configStore = useConfigStore()
const authStore = useAuthStore()

// Computed for permission
const canEdit = computed(() => authStore.isAdmin)

// Composables
const errorHandler = useErrorHandler({ showNotification: true })
const { t } = useLanguage()

// State
const selectedLanguagePairId = ref<string>('')
const selectedCatalogId = ref<string>('')
const searchText = ref('')
const showTermDialog = ref(false)
const showImportDialog = ref(false)
const editingTerm = ref<TermPair | null>(null)
const sortField = ref<string>('updatedAt')
const sortOrder = ref<'ascend' | 'descend'>('descend')

// Computed
const languagePairs = computed(() => configStore.languagePairs)

const columns = computed(() => {
  const baseColumns = [
    {
      title: t('thesaurus.sourceTerm', 'Source Term'),
      dataIndex: 'sourceTerm',
      key: 'sourceTerm',
      sorter: true,
      width: canEdit.value ? '35%' : '40%',
    },
    {
      title: t('thesaurus.targetTerm', 'Target Term'),
      dataIndex: 'targetTerm',
      key: 'targetTerm',
      sorter: true,
      width: canEdit.value ? '35%' : '40%',
    },
    {
      title: t('thesaurus.lastModified', 'Last Modified'),
      dataIndex: 'updatedAt',
      key: 'updatedAt',
      sorter: true,
      width: '20%',
    },
  ]

  if (canEdit.value) {
    baseColumns.push({
      title: t('common.actions', 'Actions'),
      key: 'actions',
      width: '10%',
      fixed: 'right' as const,
    } as any)
  }

  return baseColumns
})

const pagination = computed<TablePaginationConfig>(() => ({
  current: thesaurusStore.currentPage,
  pageSize: thesaurusStore.pageSize,
  total: thesaurusStore.totalItems,
  showSizeChanger: true,
  showQuickJumper: true,
  showTotal: (total: number) => t('thesaurus.totalTerms', { total }),
}))

// Methods
async function loadLanguagePairs() {
  try {
    // Load from localStorage first
    configStore.loadConfig()
    if (languagePairs.value.length > 0 && !selectedLanguagePairId.value) {
      const firstPair = languagePairs.value[0]
      if (firstPair) {
        selectedLanguagePairId.value = firstPair.id
        await handleLanguagePairChange(firstPair.id)
      }
    }
  } catch (err) {
    errorHandler.handleError(err, 'Load Language Pairs')
  }
}

async function handleLanguagePairChange(languagePairId: string) {
  selectedCatalogId.value = ''
  thesaurusStore.setSelectedLanguagePair(languagePairId)
  
  if (languagePairId) {
    try {
      await thesaurusStore.fetchCatalogs(languagePairId)
      // Auto-select first catalog if available
      if (thesaurusStore.catalogs.length > 0) {
        const firstCatalog = thesaurusStore.catalogs[0]
        if (firstCatalog) {
          selectedCatalogId.value = firstCatalog.id
          await handleCatalogChange(firstCatalog.id)
        }
      }
    } catch (err) {
      errorHandler.handleError(err, 'Load Catalogs')
    }
  }
}

function handleCatalogSelect(catalogId: string) {
  selectedCatalogId.value = catalogId
  handleCatalogChange(catalogId)
}

async function handleCatalogChange(catalogId: string) {
  thesaurusStore.setSelectedCatalog(catalogId)
  searchText.value = ''
  
  if (catalogId && selectedLanguagePairId.value) {
    await loadTermPairs()
  }
}

async function loadTermPairs() {
  if (!selectedLanguagePairId.value || !selectedCatalogId.value) return
  
  try {
    await thesaurusStore.fetchTermPairs(
      selectedLanguagePairId.value,
      selectedCatalogId.value,
      searchText.value || undefined,
      thesaurusStore.currentPage,
      thesaurusStore.pageSize
    )
  } catch (err) {
    errorHandler.handleError(err, 'Load Term Pairs')
  }
}

function handleSearch(value: string) {
  searchText.value = value
  thesaurusStore.setCurrentPage(1)
  loadTermPairs()
}

let searchTimeout: ReturnType<typeof setTimeout> | null = null
function handleSearchChange() {
  if (searchTimeout) clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    thesaurusStore.setCurrentPage(1)
    loadTermPairs()
  }, 300)
}

function handleTableChange(
  paginationConfig: TablePaginationConfig,
  _filters: Record<string, unknown>,
  sorter: { field?: string; order?: 'ascend' | 'descend' } | Array<{ field?: string; order?: 'ascend' | 'descend' }>
) {
  if (paginationConfig.current) {
    thesaurusStore.setCurrentPage(paginationConfig.current)
  }
  
  // Handle sorter (could be array for multi-column sort)
  const singleSorter = Array.isArray(sorter) ? sorter[0] : sorter
  if (singleSorter?.field) {
    sortField.value = singleSorter.field
    sortOrder.value = singleSorter.order || 'descend'
  }
  
  loadTermPairs()
}

function showAddTermDialog() {
  editingTerm.value = null
  showTermDialog.value = true
}

function showEditTermDialog(term: TermPair) {
  editingTerm.value = term
  showTermDialog.value = true
}

async function handleTermSaved() {
  showTermDialog.value = false
  editingTerm.value = null
  await loadTermPairs()
  // Refresh catalogs to update term counts
  if (selectedLanguagePairId.value) {
    await thesaurusStore.fetchCatalogs(selectedLanguagePairId.value)
  }
}

async function handleDeleteTerm(termId: string) {
  try {
    await thesaurusStore.deleteTermPair(termId)
    errorHandler.showSuccess(t('thesaurus.termDeleted', 'Term deleted successfully'))
    // Refresh catalogs to update term counts
    if (selectedLanguagePairId.value) {
      await thesaurusStore.fetchCatalogs(selectedLanguagePairId.value)
    }
  } catch (err) {
    errorHandler.handleError(err, 'Delete Term')
  }
}

async function handleExport() {
  if (!selectedLanguagePairId.value || !selectedCatalogId.value) return
  
  try {
    const csvContent = await thesaurusStore.exportToCsv(
      selectedLanguagePairId.value,
      selectedCatalogId.value
    )
    
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const catalog = thesaurusStore.catalogs.find(c => c.id === selectedCatalogId.value)
    const catalogName = catalog?.name || 'terms'
    const date = new Date().toISOString().split('T')[0]
    triggerBlobDownload(blob, `${catalogName}_${date}.csv`)
    
    errorHandler.showSuccess(t('thesaurus.exportSuccess', 'Export completed'))
  } catch (err) {
    errorHandler.handleError(err, 'Export CSV')
  }
}

function handleCatalogCreated(catalog: { id: string }) {
  selectedCatalogId.value = catalog.id
  handleCatalogChange(catalog.id)
}

function handleCatalogDeleted(catalogId: string) {
  if (selectedCatalogId.value === catalogId) {
    selectedCatalogId.value = ''
    thesaurusStore.setSelectedCatalog('')
  }
}

async function handleImportComplete() {
  showImportDialog.value = false
  await loadTermPairs()
  // Refresh catalogs to update term counts
  if (selectedLanguagePairId.value) {
    await thesaurusStore.fetchCatalogs(selectedLanguagePairId.value)
  }
}

function formatDate(dateString: string): string {
  if (!dateString) return 'N/A'
  return new Date(dateString).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

// Lifecycle
onMounted(() => {
  loadLanguagePairs()
})
</script>

<style scoped>
.thesaurus-page {
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

.sticky-card {
  position: sticky;
  top: 24px;
  max-height: calc(100vh - 48px);
  overflow-y: auto;
}

/* Hide scrollbar for sticky card but allow scrolling */
.sticky-card::-webkit-scrollbar {
  width: 6px;
}

.sticky-card::-webkit-scrollbar-track {
  background: transparent;
}

.sticky-card::-webkit-scrollbar-thumb {
  background-color: rgba(0, 0, 0, 0.1);
  border-radius: 10px;
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

.term-count {
  font-size: 14px;
  font-weight: 400;
  color: var(--text-secondary);
}

.catalog-select-wrapper {
  display: flex;
  gap: 8px;
}

.catalog-select-wrapper .ant-select {
  flex: 1;
}

.form-section-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-main);
}

.empty-state {
  padding: 60px 0;
  opacity: 0.6;
}

.source-term {
  font-weight: 500;
  color: var(--text-main);
}

.target-term {
  color: var(--primary-color);
}

.date-text {
  color: var(--text-secondary);
  font-size: 13px;
}

/* Responsive */
@media (max-width: 768px) {
  .content {
    padding: 16px;
  }
  
  .page-header h1 {
    font-size: 22px;
  }
  
  .sticky-card {
    position: relative;
    top: 0;
    max-height: none;
    overflow-y: visible;
  }
}
</style>
