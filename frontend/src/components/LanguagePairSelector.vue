<template>
  <div class="language-pair-selector">
    <a-form-item
      :label="t('languagePair.title')"
      :validate-status="validationStatus"
      :help="validationMessage"
      required
    >
      <a-select
        v-model:value="selectedPairId"
        :placeholder="t('languagePair.select')"
        :loading="loading"
        :disabled="disabled || loading"
        size="middle"
        @change="handleChange"
        style="width: 100%"
      >
        <a-select-option
          v-for="pair in languagePairs"
          :key="pair.id"
          :value="pair.id"
        >
          <div class="language-pair-option">
            <span class="source-language">{{ pair.sourceLanguage }}</span>
            <ArrowRightOutlined style="margin: 0 8px; color: #8c8c8c" />
            <span class="target-language">{{ pair.targetLanguage }}</span>
          </div>
        </a-select-option>
      </a-select>
    </a-form-item>

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
import { ref, computed, onMounted } from 'vue'
import { ArrowRightOutlined } from '@ant-design/icons-vue'
import { useQuery } from '@/composables/useGraphQL'
import { LANGUAGE_PAIRS_QUERY } from '@/graphql/queries'
import { useConfigStore } from '@/stores/config'
import { useLanguage } from '@/composables/useLanguage'
import type { LanguagePair } from '@/types'

// Props
interface Props {
  modelValue?: string
  disabled?: boolean
  required?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: '',
  disabled: false,
  required: true
})

// Emits
const emit = defineEmits<{
  'update:modelValue': [value: string]
  'change': [pair: LanguagePair | null]
  'error': [error: string]
}>()

// State
const selectedPairId = ref<string>(props.modelValue)
const errorMessage = ref('')
const configStore = useConfigStore()
const { t } = useLanguage()

// GraphQL query
const { data, loading, error, refetch } = useQuery<{ languagePairs: LanguagePair[] }>(
  LANGUAGE_PAIRS_QUERY,
  {}
)

// Computed
const languagePairs = computed(() => {
  return data.value?.languagePairs || configStore.languagePairs
})

const selectedPair = computed(() => {
  return languagePairs.value.find(pair => pair.id === selectedPairId.value) || null
})

const validationStatus = computed(() => {
  if (!props.required) return ''
  if (errorMessage.value) return 'error'
  if (selectedPairId.value) return 'success'
  return ''
})

const validationMessage = computed(() => {
  if (errorMessage.value) return errorMessage.value
  if (props.required && !selectedPairId.value) {
    return 'Please select a language pair'
  }
  return ''
})

// Methods
function handleChange(value: string) {
  selectedPairId.value = value
  emit('update:modelValue', value)
  emit('change', selectedPair.value)
}

async function loadLanguagePairs() {
  try {
    errorMessage.value = ''
    await refetch()
    
    if (data.value?.languagePairs) {
      configStore.setLanguagePairs(data.value.languagePairs)
      
      // 如果没有选中值且有可用选项，默认选中第一个
      if (!selectedPairId.value && data.value.languagePairs.length > 0) {
        const firstPair = data.value.languagePairs[0]
        if (firstPair) {
          selectedPairId.value = firstPair.id
          emit('update:modelValue', firstPair.id)
          emit('change', firstPair)
        }
      }
    }
  } catch (err: any) {
    const message = err.message || 'Failed to load language pairs'
    errorMessage.value = message
    emit('error', message)
    console.error('Error loading language pairs:', err)
  }
}

// Lifecycle
onMounted(() => {
  loadLanguagePairs()
})

// Expose methods for parent component
defineExpose({
  refresh: loadLanguagePairs,
  getSelectedPair: () => selectedPair.value,
  validate: () => {
    if (props.required && !selectedPairId.value) {
      errorMessage.value = 'Please select a language pair'
      return false
    }
    return true
  }
})
</script>

<style scoped>
.language-pair-selector {
  width: 100%;
}

/* 选中后显示在输入框中的内容垂直居中 */
.language-pair-selector :deep(.ant-select-selector) {
  display: flex;
  align-items: center;
}

.language-pair-selector :deep(.ant-select-selection-item) {
  display: flex;
  align-items: center;
  line-height: 1;
  font-size: 14px;
}

.language-pair-option {
  display: flex;
  align-items: center;
  padding: 4px 0;
  line-height: 1.5;
}

.source-language {
  font-weight: 500;
  color: var(--text-main);
}

.target-language {
  font-weight: 500;
  color: var(--primary-color);
}

.error-message {
  margin-top: 16px;
}

/* Mobile layout (< 768px) */
@media (max-width: 767px) {
  .language-pair-selector :deep(.ant-form-item-label) {
    font-size: 14px;
  }

  .language-pair-selector :deep(.ant-select-selector) {
    font-size: 14px;
  }

  .language-pair-option {
    font-size: 13px;
    padding: 2px 0;
  }

  .source-language,
  .target-language {
    font-size: 13px;
  }

  .language-pair-option :deep(.anticon) {
    font-size: 12px;
    margin: 0 6px;
  }

  .error-message {
    margin-top: 12px;
  }

  .error-message :deep(.ant-alert) {
    font-size: 13px;
  }
}

/* Tablet layout (768px - 1024px) */
@media (min-width: 768px) and (max-width: 1024px) {
  .language-pair-option {
    font-size: 13px;
  }

  .source-language,
  .target-language {
    font-size: 13px;
  }
}

/* Desktop layout (> 1024px) */
@media (min-width: 1025px) {
  .language-pair-option {
    font-size: 14px;
  }
}

/* Small mobile devices */
@media (max-width: 480px) {
  .language-pair-selector :deep(.ant-form-item-label) {
    font-size: 13px;
  }

  .language-pair-selector :deep(.ant-select-selector) {
    font-size: 13px;
    padding: 4px 11px;
  }

  .language-pair-option {
    font-size: 12px;
  }

  .source-language,
  .target-language {
    font-size: 12px;
  }

  .language-pair-option :deep(.anticon) {
    font-size: 11px;
    margin: 0 4px;
  }
}
</style>
