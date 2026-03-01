<script setup lang="ts">
import { onMounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
// @ts-ignore
import { ConfigProvider, theme as antTheme } from 'ant-design-vue'
import { useAuthStore } from '@/stores/auth'
import { useConfigStore } from '@/stores/config'
import { useTheme } from '@/composables/useTheme'
import ErrorNotification from '@/components/ErrorNotification.vue'
import NavigationMenu from '@/components/NavigationMenu.vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const configStore = useConfigStore()
const { initTheme, isDark } = useTheme()

// Show navigation menu only on authenticated pages (not on login, 404, or change-password)
const showNavigation = computed(() => {
  return authStore.isAuthenticated && 
         route.path !== '/login' && 
         route.path !== '/change-password'
})

const themeConfig = computed(() => ({
  algorithm: isDark.value ? antTheme.darkAlgorithm : antTheme.defaultAlgorithm,
  token: {
    colorPrimary: '#6366f1',
    borderRadius: 8,
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif",
    // We let Ant Design handle background colors in dark mode, or override with transparency where needed
    colorBgLayout: isDark.value ? '#0f172a' : '#f8fafc',
    colorBgContainer: isDark.value ? '#1e293b' : '#ffffff',
  },
}))

// Watch for mustChangePassword and redirect if needed
watch(
  () => authStore.mustChangePassword,
  (mustChange) => {
    if (mustChange && authStore.isAuthenticated && route.path !== '/change-password') {
      router.push('/change-password')
    }
  },
  { immediate: true }
)

onMounted(() => {
  initTheme()
  // Load persisted state on app startup
  authStore.loadAuth()
  configStore.loadConfig()
  // Note: Job history is fetched on MainPage when user navigates there
})
</script>

<template>
  <a-config-provider :theme="themeConfig">
    <div id="app">
      <ErrorNotification />
      <a-layout class="app-layout">
        <NavigationMenu v-if="showNavigation" />
        <a-layout-content class="app-content">
          <router-view />
        </a-layout-content>
      </a-layout>
    </div>
  </a-config-provider>
</template>

<style>
/* Global resets and utility classes are in style.css */

.app-layout {
  min-height: 100vh;
  background: var(--bg-color);
}

.app-content {
  background: var(--bg-color);
}

/* Remove default padding for pages that handle their own layout */
.app-content :deep(.ant-layout-content) {
  padding: 0;
}

/* Smooth scrolling */
html {
  scroll-behavior: smooth;
}

/* Improve touch targets on mobile */
@media (max-width: 767px) {
  button,
  a,
  input,
  select,
  textarea {
    min-height: 44px;
    min-width: 44px;
  }
}

/* Prevent horizontal scroll on mobile */
body {
  overflow-x: hidden;
}

/* Improve readability */
p,
li,
td,
th {
  line-height: 1.6;
}

/* Focus styles for accessibility */
:focus-visible {
  outline: 2px solid var(--primary-color);
  outline-offset: 2px;
}

/* Reduce motion for users who prefer it */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}

/* Print styles */
@media print {
  .app-layout {
    background: white;
  }

  .app-content {
    background: white;
  }

  /* Hide interactive elements when printing */
  button,
  .ant-btn {
    display: none;
  }
}
</style>
