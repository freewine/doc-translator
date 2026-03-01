<template>
  <a-modal
    :open="visible"
    :title="isEditing ? t('thesaurus.editTerm', 'Edit Term') : t('thesaurus.addTerm', 'Add Term')"
    :ok-text="isEditing ? t('common.save') : t('common.add')"
    :cancel-text="t('common.cancel')"
    :confirm-loading="isSubmitting"
    @ok="handleSubmit"
    @cancel="handleClose"
  >
    <a-form
      ref="formRef"
      :model="formState"
      :rules="rules"
      layout="vertical"
      @finish="handleSubmit"
    >
      <a-form-item
        :label="t('thesaurus.sourceTerm', 'Source Term')"
        name="sourceTerm"
      >
        <a-input
          v-model:value="formState.sourceTerm"
          :placeholder="t('thesaurus.sourceTermPlaceholder', 'Enter source term')"
          :disabled="isEditing"
          :maxlength="500"
          show-count
        />
        <template v-if="isEditing" #extra>
          <span class="hint-text">{{ t('thesaurus.sourceTermReadonly', 'Source term cannot be changed when editing') }}</span>
        </template>
      </a-form-item>

      <a-form-item
        :label="t('thesaurus.targetTerm', 'Target Term')"
        name="targetTerm"
      >
        <a-input
          v-model:value="formState.targetTerm"
          :placeholder="t('thesaurus.targetTermPlaceholder', 'Enter target term translation')"
          :maxlength="500"
          show-count
        />
      </a-form-item>
    </a-form>
  </a-modal>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import type { FormInstance, Rule } from 'ant-design-vue/es/form'
import { useThesaurusStore } from '@/stores/thesaurus'
import { useErrorHandler } from '@/composables/useErrorHandler'
import { useLanguage } from '@/composables/useLanguage'
import type { TermPair } from '@/types'

// Props
interface Props {
  visible: boolean
  term: TermPair | null
  languagePairId: string
  catalogId: string
}

const props = defineProps<Props>()

// Emits
const emit = defineEmits<{
  'update:visible': [value: boolean]
  'saved': []
}>()

// Stores
const thesaurusStore = useThesaurusStore()

// Composables
const errorHandler = useErrorHandler({ showNotification: true })
const { t } = useLanguage()

// State
const formRef = ref<FormInstance>()
const isSubmitting = ref(false)
const formState = reactive({
  sourceTerm: '',
  targetTerm: '',
})

// Computed
const isEditing = computed(() => !!props.term)

// Validation rules
const rules: Record<string, Rule[]> = {
  sourceTerm: [
    { required: true, message: t('validation.required'), trigger: 'blur' },
    { 
      validator: (_rule: Rule, value: string) => {
        if (value && value.trim().length === 0) {
          return Promise.reject(t('thesaurus.emptyTermError', 'Term cannot be empty or whitespace only'))
        }
        return Promise.resolve()
      },
      trigger: 'blur'
    },
    {
      max: 500,
      message: t('thesaurus.termTooLong', 'Term cannot exceed 500 characters'),
      trigger: 'blur'
    }
  ],
  targetTerm: [
    { required: true, message: t('validation.required'), trigger: 'blur' },
    { 
      validator: (_rule: Rule, value: string) => {
        if (value && value.trim().length === 0) {
          return Promise.reject(t('thesaurus.emptyTermError', 'Term cannot be empty or whitespace only'))
        }
        return Promise.resolve()
      },
      trigger: 'blur'
    },
    {
      max: 500,
      message: t('thesaurus.termTooLong', 'Term cannot exceed 500 characters'),
      trigger: 'blur'
    }
  ],
}

// Watch for term changes (when editing)
watch(() => props.term, (newTerm) => {
  if (newTerm) {
    formState.sourceTerm = newTerm.sourceTerm
    formState.targetTerm = newTerm.targetTerm
  } else {
    resetForm()
  }
}, { immediate: true })

// Watch for visibility changes
watch(() => props.visible, (isVisible) => {
  if (!isVisible) {
    resetForm()
  } else if (props.term) {
    formState.sourceTerm = props.term.sourceTerm
    formState.targetTerm = props.term.targetTerm
  }
})

// Methods
function resetForm() {
  formState.sourceTerm = ''
  formState.targetTerm = ''
  formRef.value?.resetFields()
}

function handleClose() {
  emit('update:visible', false)
  resetForm()
}

async function handleSubmit() {
  if (!props.languagePairId || !props.catalogId) {
    errorHandler.handleError('Language pair and catalog must be selected', 'Validation')
    return
  }

  try {
    await formRef.value?.validate()
  } catch {
    return
  }

  isSubmitting.value = true
  try {
    if (isEditing.value && props.term) {
      // Edit existing term
      await thesaurusStore.editTermPair(props.term.id, formState.targetTerm.trim())
      errorHandler.showSuccess(t('thesaurus.termUpdated', 'Term updated successfully'))
    } else {
      // Add new term
      await thesaurusStore.addTermPair(
        props.languagePairId,
        props.catalogId,
        formState.sourceTerm.trim(),
        formState.targetTerm.trim()
      )
      errorHandler.showSuccess(t('thesaurus.termAdded', 'Term added successfully'))
    }
    emit('saved')
    handleClose()
  } catch (err) {
    errorHandler.handleError(err, isEditing.value ? 'Edit Term' : 'Add Term')
  } finally {
    isSubmitting.value = false
  }
}
</script>

<style scoped>
.hint-text {
  color: var(--text-secondary);
  font-size: 12px;
}
</style>
