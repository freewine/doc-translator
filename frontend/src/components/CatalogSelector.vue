<template>
  <div class="catalog-selector">
    <div v-if="catalogs.length === 0" class="empty-state">
      <span class="empty-text">{{ t('thesaurus.noCatalogsAvailable', 'No catalogs available for this language pair') }}</span>
    </div>

    <div v-else class="catalog-list">
      <!-- Available Catalogs -->
      <div class="available-section">
        <div class="section-label">{{ t('thesaurus.availableCatalogs', 'Available') }}</div>
        <div class="catalog-items">
          <div
            v-for="catalog in availableCatalogs"
            :key="catalog.id"
            class="catalog-item"
            @click="selectCatalog(catalog.id)"
          >
            <a-checkbox :checked="false" />
            <span class="catalog-name">{{ catalog.name }}</span>
            <span class="term-count">({{ catalog.termCount }})</span>
          </div>
        </div>
      </div>

      <!-- Selected Catalogs (with drag to reorder) -->
      <div v-if="selectedCatalogIds.length > 0" class="selected-section">
        <div class="section-label">
          {{ t('thesaurus.selectedCatalogs', 'Selected') }}
          <span class="priority-hint">{{ t('thesaurus.dragToReorder', '(drag to reorder priority)') }}</span>
        </div>
        <div class="selected-items" ref="sortableContainer">
          <div
            v-for="(catalogId, index) in selectedCatalogIds"
            :key="catalogId"
            class="selected-item"
            draggable="true"
            @dragstart="handleDragStart($event, index)"
            @dragover="handleDragOver($event, index)"
            @dragend="handleDragEnd"
            :class="{ 'dragging': dragIndex === index, 'drag-over': dragOverIndex === index }"
          >
            <HolderOutlined class="drag-handle" />
            <span class="priority-badge">{{ index + 1 }}</span>
            <span class="catalog-name">{{ getCatalogName(catalogId) }}</span>
            <span class="term-count">({{ getCatalogTermCount(catalogId) }})</span>
            <a-button type="text" size="small" @click.stop="deselectCatalog(catalogId)">
              <CloseOutlined />
            </a-button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="selectedCatalogIds.length > 0" class="summary">
      <span>{{ t('thesaurus.totalTermsSelected', 'Total terms') }}: {{ totalTermCount }}</span>
      <span v-if="totalTermCount > 200" class="warning-text">
        <WarningOutlined />
        {{ t('thesaurus.termLimitWarning', 'Only first 200 terms will be used') }}
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useThesaurusStore } from '@/stores/thesaurus'
import { useLanguage } from '@/composables/useLanguage'
import type { Catalog } from '@/types'
import {
  HolderOutlined,
  CloseOutlined,
  WarningOutlined,
} from '@ant-design/icons-vue'

// Props
interface Props {
  modelValue: string[]
  languagePairId: string
}

const props = defineProps<Props>()

// Emits
const emit = defineEmits<{
  'update:modelValue': [value: string[]]
}>()

// Stores
const thesaurusStore = useThesaurusStore()

// Composables
const { t } = useLanguage()

// State
const selectedCatalogIds = ref<string[]>([...props.modelValue])
const dragIndex = ref<number | null>(null)
const dragOverIndex = ref<number | null>(null)

// Computed
const catalogs = computed(() => thesaurusStore.catalogs)

const availableCatalogs = computed(() => 
  catalogs.value.filter(c => !selectedCatalogIds.value.includes(c.id))
)

const totalTermCount = computed(() => 
  selectedCatalogIds.value.reduce((sum, id) => {
    const catalog = catalogs.value.find(c => c.id === id)
    return sum + (catalog?.termCount || 0)
  }, 0)
)

// Watch for external changes
watch(() => props.modelValue, (newValue) => {
  selectedCatalogIds.value = [...newValue]
}, { deep: true })

// Watch for language pair changes
watch(() => props.languagePairId, async (newId) => {
  if (newId) {
    await thesaurusStore.fetchCatalogs(newId)
    // Clear selection when language pair changes
    selectedCatalogIds.value = []
    emitChange()
  }
}, { immediate: true })

// Methods
function getCatalogName(catalogId: string): string {
  const catalog = catalogs.value.find(c => c.id === catalogId)
  return catalog?.name || 'Unknown'
}

function getCatalogTermCount(catalogId: string): number {
  const catalog = catalogs.value.find(c => c.id === catalogId)
  return catalog?.termCount || 0
}

function selectCatalog(catalogId: string) {
  if (!selectedCatalogIds.value.includes(catalogId)) {
    selectedCatalogIds.value.push(catalogId)
    emitChange()
  }
}

function deselectCatalog(catalogId: string) {
  const index = selectedCatalogIds.value.indexOf(catalogId)
  if (index !== -1) {
    selectedCatalogIds.value.splice(index, 1)
    emitChange()
  }
}

function emitChange() {
  emit('update:modelValue', [...selectedCatalogIds.value])
}

// Drag and drop handlers
function handleDragStart(event: DragEvent, index: number) {
  dragIndex.value = index
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move'
  }
}

function handleDragOver(event: DragEvent, index: number) {
  event.preventDefault()
  if (dragIndex.value !== null && dragIndex.value !== index) {
    dragOverIndex.value = index
  }
}

function handleDragEnd() {
  if (dragIndex.value !== null && dragOverIndex.value !== null && dragIndex.value !== dragOverIndex.value) {
    // Reorder the array
    const item = selectedCatalogIds.value[dragIndex.value]
    if (item !== undefined) {
      selectedCatalogIds.value.splice(dragIndex.value, 1)
      selectedCatalogIds.value.splice(dragOverIndex.value, 0, item)
      emitChange()
    }
  }
  dragIndex.value = null
  dragOverIndex.value = null
}
</script>

<style scoped>
.catalog-selector {
  background: var(--surface-color);
}

.empty-state {
  padding: 24px;
  text-align: center;
}

.empty-text {
  color: var(--text-secondary);
  font-size: 14px;
}

.catalog-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.section-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  margin-bottom: 8px;
}

.priority-hint {
  font-weight: 400;
  text-transform: none;
  margin-left: 8px;
}

.catalog-items {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.catalog-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.catalog-item:hover {
  background: var(--item-hover-bg);
}

.catalog-name {
  flex: 1;
  color: var(--text-main);
}

.term-count {
  color: var(--text-secondary);
  font-size: 13px;
}

.selected-items {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.selected-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 6px;
  background: rgba(99, 102, 241, 0.08);
  border: 1px solid transparent;
  cursor: grab;
  transition: all 0.2s;
}

.selected-item:hover {
  border-color: var(--primary-color);
}

.selected-item.dragging {
  opacity: 0.5;
}

.selected-item.drag-over {
  border-color: var(--primary-color);
  border-style: dashed;
}

.drag-handle {
  color: var(--text-secondary);
  cursor: grab;
}

.priority-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--primary-color);
  color: white;
  font-size: 11px;
  font-weight: 600;
}

.summary {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border-color);
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  color: var(--text-secondary);
}

.warning-text {
  color: var(--warning-color, #faad14);
  display: flex;
  align-items: center;
  gap: 4px;
}
</style>
