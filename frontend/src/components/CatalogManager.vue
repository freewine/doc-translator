<template>
  <div class="catalog-sidebar-manager">
    <!-- Existing Catalogs List -->
    <div class="catalogs-section">
      <div class="section-header">
        <h4>{{ t('thesaurus.termCatalogs') }}</h4>
        <a-button type="text" size="small" @click="toggleCreateForm" v-if="canEdit" class="add-btn">
          <PlusOutlined />
        </a-button>
      </div>
      
      <!-- Create New Catalog (Inline Form) -->
      <div v-if="showCreateForm && canEdit" class="create-section mb-16">
        <a-form layout="vertical" :model="newCatalog" @finish="handleCreateCatalog">
          <a-form-item
            name="name"
            :rules="[{ required: true, message: t('validation.required', 'Required'), trigger: 'blur' }]"
            class="mb-8"
          >
            <a-input
              v-model:value="newCatalog.name"
              :placeholder="t('thesaurus.catalogNamePlaceholder', 'New catalog name...')"
              :maxlength="100"
              size="middle"
              @pressEnter="handleCreateCatalog"
              auto-focus
            />
          </a-form-item>
          <div class="create-actions">
            <a-button size="small" @click="showCreateForm = false" class="mr-8">
              {{ t('common.cancel', 'Cancel') }}
            </a-button>
            <a-button
              type="primary"
              size="small"
              html-type="submit"
              :loading="isCreating"
              :disabled="!newCatalog.name.trim()"
            >
              {{ t('common.save', 'Save') }}
            </a-button>
          </div>
        </a-form>
      </div>

      <div v-if="thesaurusStore.catalogs.length === 0" class="empty-state">
        <a-empty :description="t('thesaurus.noCatalogsAvailable', 'No catalogs available for this language pair')" :image="false" />
      </div>

      <div v-else class="custom-catalog-list">
        <a-spin :spinning="thesaurusStore.isLoading">
          <div 
            v-for="item in thesaurusStore.catalogs"
            :key="item.id"
            class="catalog-list-item" 
            :class="{ 'is-selected': selectedCatalogId === item.id }"
            @click="handleSelect(item.id)"
          >
            <div class="item-content">
              <div v-if="renamingId === item.id" class="rename-form" @click.stop>
                <a-input
                  v-model:value="renameValue"
                  size="small"
                  style="width: 140px"
                  @pressEnter="handleRename(item.id)"
                  auto-focus
                />
                <a-button type="text" size="small" @click="handleRename(item.id)">
                  <CheckOutlined />
                </a-button>
                <a-button type="text" size="small" @click="cancelRename">
                  <CloseOutlined />
                </a-button>
              </div>
              <div v-else class="catalog-info">
                <span class="catalog-name">{{ item.name }}</span>
                <span class="term-count-badge">{{ item.termCount }}</span>
              </div>
            </div>
            
            <div class="item-actions" v-if="canEdit" @click.stop>
              <a-button type="text" size="small" @click="startRename(item)">
                <EditOutlined />
              </a-button>
              <a-popconfirm
                :title="t('thesaurus.confirmDeleteCatalog', 'Delete this catalog and all its terms?')"
                :ok-text="t('common.yes', 'Yes')"
                :cancel-text="t('common.no', 'No')"
                @confirm="handleDeleteCatalog(item.id)"
              >
                <a-button type="text" size="small" danger :loading="deletingId === item.id">
                  <DeleteOutlined />
                </a-button>
              </a-popconfirm>
            </div>
          </div>
        </a-spin>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch, computed } from 'vue'
import { useThesaurusStore } from '@/stores/thesaurus'
import { useAuthStore } from '@/stores/auth'
import { useErrorHandler } from '@/composables/useErrorHandler'
import { useLanguage } from '@/composables/useLanguage'
import type { Catalog } from '@/types'
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  CheckOutlined,
  CloseOutlined,
} from '@ant-design/icons-vue'

// Props
interface Props {
  languagePairId: string
  selectedCatalogId?: string
}

const props = defineProps<Props>()

// Emits
const emit = defineEmits<{
  'select': [catalogId: string]
  'catalog-created': [catalog: Catalog]
  'catalog-deleted': [catalogId: string]
}>()

// Stores
const thesaurusStore = useThesaurusStore()
const authStore = useAuthStore()

// Computed for permission
const canEdit = computed(() => authStore.isAdmin)

// Composables
const errorHandler = useErrorHandler({ showNotification: true })
const { t } = useLanguage()

// State
const showCreateForm = ref(false)
const newCatalog = reactive({
  name: '',
})
const isCreating = ref(false)
const renamingId = ref<string | null>(null)
const renameValue = ref('')
const deletingId = ref<string | null>(null)

// Watch for language pair changes
watch(() => props.languagePairId, async (newId) => {
  if (newId) {
    await thesaurusStore.fetchCatalogs(newId)
  }
})

// Methods
function handleSelect(catalogId: string) {
  emit('select', catalogId)
}

function toggleCreateForm() {
  showCreateForm.value = !showCreateForm.value
  if (showCreateForm.value) {
    newCatalog.name = ''
  }
}

async function handleCreateCatalog() {
  if (!props.languagePairId || !newCatalog.name.trim()) return
  
  isCreating.value = true
  try {
    const catalog = await thesaurusStore.createCatalog(
      props.languagePairId,
      newCatalog.name.trim()
    )
    errorHandler.showSuccess(t('thesaurus.catalogCreated', 'Catalog created successfully'))
    emit('catalog-created', catalog)
    newCatalog.name = ''
    showCreateForm.value = false
  } catch (err) {
    errorHandler.handleError(err, 'Create Catalog')
  } finally {
    isCreating.value = false
  }
}

function startRename(catalog: Catalog) {
  renamingId.value = catalog.id
  renameValue.value = catalog.name
}

function cancelRename() {
  renamingId.value = null
  renameValue.value = ''
}

async function handleRename(catalogId: string) {
  if (!props.languagePairId || !renameValue.value.trim()) {
    cancelRename()
    return
  }
  
  try {
    await thesaurusStore.updateCatalog(
      props.languagePairId,
      catalogId,
      renameValue.value.trim()
    )
    errorHandler.showSuccess(t('thesaurus.catalogRenamed', 'Catalog renamed successfully'))
    cancelRename()
  } catch (err) {
    errorHandler.handleError(err, 'Rename Catalog')
  }
}

async function handleDeleteCatalog(catalogId: string) {
  if (!props.languagePairId) return
  
  deletingId.value = catalogId
  try {
    const deletedCount = await thesaurusStore.deleteCatalog(props.languagePairId, catalogId)
    errorHandler.showSuccess(
      t('thesaurus.catalogDeleted', 'Catalog deleted'),
      t('thesaurus.catalogDeletedTerms', { count: deletedCount })
    )
    emit('catalog-deleted', catalogId)
  } catch (err) {
    errorHandler.handleError(err, 'Delete Catalog')
  } finally {
    deletingId.value = null
  }
}
</script>

<style scoped>
.catalog-sidebar-manager {
  display: flex;
  flex-direction: column;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.section-header h4 {
  margin: 0;
  font-weight: 600;
  color: var(--text-main);
  font-size: 15px;
}

.add-btn {
  color: var(--primary-color);
}

.create-section {
  background: rgba(0, 0, 0, 0.02);
  padding: 12px;
  border-radius: 8px;
  margin-bottom: 16px;
}

.mb-8 {
  margin-bottom: 8px;
}

.mb-16 {
  margin-bottom: 16px;
}

.mr-8 {
  margin-right: 8px;
}

.create-actions {
  display: flex;
  justify-content: flex-end;
}

.empty-state {
  padding: 24px 0;
}

.custom-catalog-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.catalog-list-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid transparent;
}

.catalog-list-item:hover {
  background-color: rgba(0, 0, 0, 0.02);
}

.catalog-list-item.is-selected {
  background-color: var(--primary-color-light, #e6f4ff);
  border-color: var(--primary-color-border, #91caff);
}

.catalog-list-item.is-selected .catalog-name {
  color: var(--primary-color);
  font-weight: 600;
}

.item-content {
  flex: 1;
  overflow: hidden;
}

.catalog-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.catalog-name {
  font-weight: 500;
  color: var(--text-main);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 140px;
}

.term-count-badge {
  background-color: rgba(0, 0, 0, 0.04);
  color: var(--text-secondary);
  font-size: 12px;
  padding: 2px 6px;
  border-radius: 10px;
  font-weight: 500;
}

.is-selected .term-count-badge {
  background-color: var(--primary-color);
  color: #fff;
}

.item-actions {
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.2s;
}

.catalog-list-item:hover .item-actions,
.catalog-list-item.is-selected .item-actions {
  opacity: 1;
}

.rename-form {
  display: flex;
  align-items: center;
  gap: 4px;
}

/* Dark mode adjustments */
@media (prefers-color-scheme: dark) {
  .create-section {
    background: rgba(255, 255, 255, 0.04);
  }
  
  .catalog-list-item:hover {
    background-color: rgba(255, 255, 255, 0.04);
  }
  
  .catalog-list-item.is-selected {
    background-color: rgba(23, 125, 220, 0.15);
    border-color: rgba(23, 125, 220, 0.3);
  }
  
  .term-count-badge {
    background-color: rgba(255, 255, 255, 0.1);
  }
  
  .is-selected .term-count-badge {
    color: #fff;
  }
}
</style>