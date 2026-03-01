<template>
  <div class="not-found-page">
    <a-result
      status="404"
      :title="t('notFound.title')"
      :sub-title="t('notFound.subtitle')"
      class="glass-card"
    >
      <template #extra>
        <a-space>
          <a-button type="primary" @click="goHome">
            {{ t('notFound.backHome') }}
          </a-button>
          <a-button @click="goBack">
            {{ t('notFound.goBack') }}
          </a-button>
        </a-space>
      </template>
    </a-result>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useLanguage } from '@/composables/useLanguage'

const router = useRouter()
const authStore = useAuthStore()
const { t } = useLanguage()

function goHome() {
  // Redirect to main page if authenticated, otherwise to login
  if (authStore.isAuthenticated) {
    router.push('/main')
  } else {
    router.push('/login')
  }
}

function goBack() {
  router.back()
}
</script>

<style scoped>
.not-found-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: var(--bg-color);
  padding: 24px;
}

.not-found-page :deep(.ant-result) {
  padding: 48px 32px;
  max-width: 500px;
  width: 100%;
}

/* Responsive design */
@media (max-width: 768px) {
  .not-found-page :deep(.ant-result) {
    padding: 32px 20px;
  }
}
</style>
