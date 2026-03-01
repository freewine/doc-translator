<template>
  <a-alert
    v-if="error"
    :message="displayTitle"
    :description="description"
    :type="type"
    :closable="closable"
    :show-icon="showIcon"
    class="error-display"
    @close="handleClose"
  >
    <template v-if="retryable && onRetry" #action>
      <a-button
        size="small"
        type="primary"
        :loading="isRetrying"
        @click="handleRetry"
      >
        {{ isRetrying ? t('error.retrying') : t('error.retry') }}
      </a-button>
    </template>
  </a-alert>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useLanguage } from '@/composables/useLanguage'

const { t } = useLanguage()

interface Props {
  error?: string | Error | null
  title?: string
  type?: 'error' | 'warning' | 'info' | 'success'
  closable?: boolean
  showIcon?: boolean
  retryable?: boolean
  isRetrying?: boolean
  onRetry?: () => void | Promise<void>
  onClose?: () => void
}

const props = withDefaults(defineProps<Props>(), {
  error: null,
  title: undefined,
  type: 'error',
  closable: true,
  showIcon: true,
  retryable: false,
  isRetrying: false,
})

const emit = defineEmits<{
  close: []
  retry: []
}>()

const displayTitle = computed(() => {
  return props.title || t('error.defaultTitle')
})

const description = computed(() => {
  if (!props.error) return ''

  if (typeof props.error === 'string') {
    return props.error
  }

  if (props.error instanceof Error) {
    return props.error.message
  }

  return t('error.unexpectedError')
})

function handleClose() {
  emit('close')
  if (props.onClose) {
    props.onClose()
  }
}

async function handleRetry() {
  emit('retry')
  if (props.onRetry) {
    await props.onRetry()
  }
}
</script>

<style scoped>
.error-display {
  margin-bottom: 16px;
}

.error-display :deep(.ant-alert-action) {
  margin-left: 8px;
}
</style>
