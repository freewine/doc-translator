<template>
  <a-modal
    :open="visible"
    :title="t('thesaurus.manageCatalogs', 'Manage Catalogs')"
    :footer="null"
    width="600px"
    @cancel="handleClose"
  >
    <div class="catalog-manager">
      <!-- Create New Catalog -->
      <div class="create-section">
        <h4>{{ t('thesaurus.createCatalog', 'Create New Catalog') }}</h4>
        <a-form layout="vertical" :model="newCatalog" @finish="handleCreateCatalog">
          <a-row :gutter="16">
            <a-col :span="12">
              <a-form-item
                :label="t('thesaurus.catalogName', 'Name')"
                name="name"
                :rules="[{ required: true, message: t('validation.required'), trigger: 'blur' }]"
              >
                <a-input
                  v-model:value="newCatalog.name"
                  :placeholder="t('thesaurus.catalogNamePlaceholder', 'e.g., IT Terms')"
                  :maxlength="100"
                />
              </a-form-item>
            </a-col>
            <a-col :span="12">
              <a-form-item :label="t('thesaurus.catalogDescription', 'Description')">
                <a-input
                  v-model:value="newCatalog.description"
                  :placeholder="t('thesaurus.catalogDescriptionPlaceholder', 'Optional description')"
                  :maxlength="500"
                />
              </a-form-item>
            </a-col>
          </a-row>
          <a-button
            type="primary"
            html-type="submit"
            :loading="isCreating"
            :disabled="!newCatalog.name.trim()"
          >
            <PlusOutlined />
            {{ t('thesaurus.createCatalog', 'Create Catalog') }}
          </a-button>
        </a-form>
      </div>

      <a-divider />

      <!-- Existing Catalogs List -->
      <div class="catalogs-section">
        <h4>{{ t('thesaurus.existingCatalogs', 'Existing Catalogs') }}</h4>
        
        <div v-if="thesaurusStore.catalogs.length === 0" class="empty-state">
          <a-empty :description="t('thesaurus.noCatalogs', 'No catalogs yet')" />
        </div>

        <a-list
          v-else
          :data-source="thesaurusStore.catalogs"
          :loading="thesaurusStore.isLoading"
          item-layout="horizontal"
        >
          <template #renderItem="{ item }">
            <a-list-item class="catalog-item">
              <template #actions>
                <a-button type="text" size="small" @click="startRename(item)">
                  <EditOutlined />
                </a-button>
                <a-popconfirm
                  :title="t('thesaurus.confirmDeleteCatalog', 'Delete this catalog and all its terms?')"
                  :ok-text="t('common.yes')"
                  :cancel-text="t('common.no')"
                  @confirm="handleDeleteCatalog(item.id)"
                >
                  <a-button type="text" size="small" danger :loading="deletingId === item.id">
                    <DeleteOutlined />
                  </a-button>
                </a-popconfirm>
              </template>
              <a-list-item-meta>
                <template #title>
                  <div v-if="renamingId === item.id" class="rename-form">
                    <a-input
                      v-model:value="renameValue"
                      size="small"
                      style="width: 200px"
                      @pressEnter="handleRename(item.id)"
                    />
                    <a-button type="text" size="small" @click="handleRename(item.id)">
                      <CheckOutlined />
                    </a-button>
                    <a-button type="text" size="small" @click="cancelRename">
                      <CloseOutlined />
                    </a-button>
                  </div>
                  <span v-else class="catalog-name">{{ item.name }}</span>
                </template>
                <template #description>
                  <div class="catalog-meta">
                    <span class="term-count">
                      {{ item.termCount }} {{ t('thesaurus.terms', 'terms') }}
                    </span>
                    <span v-if="item.description" class="catalog-description">
                      · {{ item.description }}
                    </span>
                  </div>
                </template>
              </a-list-item-meta>
            </a-list-item>
          </template>
        </a-list>
      </div>
    </div>
  </a-modal>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from 'vue'
import { useThesaurusStore } from '@/stores/thesaurus'
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
  visible: boolean
  languagePairId: string
}

const props = defineProps<Props>()

// Emits
const emit = defineEmits<{
  'update:visible': [value: boolean]
  'catalog-created': [catalog: Catalog]
  'catalog-deleted': [catalogId: string]
}>()

// Stores
const thesaurusStore = useThesaurusStore()

// Composables
const errorHandler = useErrorHandler({ showNotification: true })
const { t } = useLanguage()

// State
const newCatalog = reactive({
  name: '',
  description: '',
})
const isCreating = ref(false)
const renamingId = ref<string | null>(null)
const renameValue = ref('')
const deletingId = ref<string | null>(null)

// Watch for language pair changes
watch(() => props.languagePairId, async (newId) => {
  if (newId && props.visible) {
    await thesaurusStore.fetchCatalogs(newId)
  }
})

// Watch for visibility changes
watch(() => props.visible, async (isVisible) => {
  if (isVisible && props.languagePairId) {
    await thesaurusStore.fetchCatalogs(props.languagePairId)
  }
})

// Methods
function handleClose() {
  emit('update:visible', false)
  resetForm()
}

function resetForm() {
  newCatalog.name = ''
  newCatalog.description = ''
  renamingId.value = null
  renameValue.value = ''
}

async function handleCreateCatalog() {
  if (!props.languagePairId || !newCatalog.name.trim()) return
  
  isCreating.value = true
  try {
    const catalog = await thesaurusStore.createCatalog(
      props.languagePairId,
      newCatalog.name.trim(),
      newCatalog.description.trim() || undefined
    )
    errorHandler.showSuccess(t('thesaurus.catalogCreated', 'Catalog created successfully'))
    emit('catalog-created', catalog)
    newCatalog.name = ''
    newCatalog.description = ''
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
      `${deletedCount} terms were also deleted`
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
.catalog-manager {
  padding: 8px 0;
}

.create-section h4,
.catalogs-section h4 {
  margin-bottom: 16px;
  font-weight: 600;
  color: var(--text-main);
}

.empty-state {
  padding: 32px 0;
}

.catalog-item {
  padding: 12px 0;
}

.catalog-name {
  font-weight: 500;
  color: var(--text-main);
}

.catalog-meta {
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--text-secondary);
  font-size: 13px;
}

.term-count {
  color: var(--primary-color);
  font-weight: 500;
}

.catalog-description {
  color: var(--text-secondary);
}

.rename-form {
  display: flex;
  align-items: center;
  gap: 4px;
}
</style>
