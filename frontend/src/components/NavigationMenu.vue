<template>
  <a-layout-header class="navigation-header glass">
    <div class="nav-container">
      <div class="nav-logo" @click="router.push('/main')">
        <img src="/logo.svg" class="logo-icon" alt="Logo" />
        <span class="logo-text">{{ t('app.title') }}</span>
      </div>

      <!-- Desktop Navigation -->
      <a-menu
        v-if="authStore.isAuthenticated"
        v-model:selectedKeys="selectedKeys"
        mode="horizontal"
        class="nav-menu desktop-menu"
        @select="handleMenuSelect"
      >
        <a-menu-item key="/main">
          <template #icon>
            <HomeOutlined />
          </template>
          {{ t('nav.main') }}
        </a-menu-item>
        <a-menu-item key="/thesaurus">
          <template #icon>
            <BookOutlined />
          </template>
          {{ t('nav.thesaurus', 'Thesaurus') }}
        </a-menu-item>
        <a-menu-item v-if="authStore.isAdmin" key="/users">
          <template #icon>
            <TeamOutlined />
          </template>
          {{ t('nav.users', '用户管理') }}
        </a-menu-item>
        <a-menu-item key="/settings">
          <template #icon>
            <SettingOutlined />
          </template>
          {{ t('nav.settings') }}
        </a-menu-item>
      </a-menu>

      <!-- User Menu -->
      <div v-if="authStore.isAuthenticated" class="nav-user">
        <ThemeSwitcher />
        <LanguageSwitcher class="language-switcher" />
        <a-dropdown :trigger="['click']">
          <a-button type="text" class="user-button">
            <a-avatar size="small" class="user-avatar" :style="{ backgroundColor: 'var(--primary-color)' }">
              {{ (authStore.user?.username || 'U').charAt(0).toUpperCase() }}
            </a-avatar>
            <span class="username">{{ authStore.user?.username || 'User' }}</span>
            <DownOutlined class="dropdown-icon" />
          </a-button>
          <template #overlay>
            <a-menu class="user-dropdown-menu">
              <a-menu-item key="logout" @click="handleLogout" class="logout-item">
                <LogoutOutlined />
                {{ t('nav.logout') }}
              </a-menu-item>
            </a-menu>
          </template>
        </a-dropdown>
      </div>

      <!-- Mobile Menu Button -->
      <a-button
        v-if="authStore.isAuthenticated"
        type="text"
        class="mobile-menu-button"
        @click="showMobileMenu = true"
      >
        <MenuOutlined />
      </a-button>
    </div>

    <!-- Mobile Drawer Menu -->
    <a-drawer
      v-model:open="showMobileMenu"
      placement="right"
      :title="drawerTitle"
      :width="280"
      class="mobile-menu-drawer"
    >
      <div class="mobile-drawer-content">
        <div class="mobile-user-info" v-if="authStore.user">
           <a-avatar size="large" :style="{ backgroundColor: 'var(--primary-color)' }">
              {{ (authStore.user.username || 'U').charAt(0).toUpperCase() }}
           </a-avatar>
           <span class="mobile-username">{{ authStore.user.username }}</span>
        </div>
        
        <div class="mobile-controls">
           <div class="control-row">
             <span class="control-label">{{ t('settings.uiLanguage') }}</span>
             <LanguageSwitcher />
           </div>
           <div class="control-row">
             <span class="control-label">{{ t('settings.appearance', 'Appearance') }}</span>
             <ThemeSwitcher />
           </div>
        </div>
        
        <a-menu
          v-model:selectedKeys="selectedKeys"
          mode="inline"
          class="mobile-nav-menu"
          @select="handleMobileMenuSelect"
        >
          <a-menu-item key="/main">
            <template #icon>
              <HomeOutlined />
            </template>
            {{ t('nav.main') }}
          </a-menu-item>
          <a-menu-item key="/thesaurus">
            <template #icon>
              <BookOutlined />
            </template>
            {{ t('nav.thesaurus', 'Thesaurus') }}
          </a-menu-item>
          <a-menu-item v-if="authStore.isAdmin" key="/users">
            <template #icon>
              <TeamOutlined />
            </template>
            {{ t('nav.users', '用户管理') }}
          </a-menu-item>
          <a-menu-item key="/settings">
            <template #icon>
              <SettingOutlined />
            </template>
            {{ t('nav.settings') }}
          </a-menu-item>
          <a-divider style="margin: 8px 0" />
          <a-menu-item key="logout" @click="handleLogout" class="danger-item">
            <template #icon>
              <LogoutOutlined />
            </template>
            {{ t('nav.logout') }}
          </a-menu-item>
        </a-menu>
      </div>
    </a-drawer>
  </a-layout-header>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useErrorHandler } from '@/composables/useErrorHandler'
import { useLanguage } from '@/composables/useLanguage'
import LanguageSwitcher from './LanguageSwitcher.vue'
import ThemeSwitcher from './ThemeSwitcher.vue'
import {
  HomeOutlined,
  SettingOutlined,
  UserOutlined,
  LogoutOutlined,
  DownOutlined,
  MenuOutlined,
  BookOutlined,
  TeamOutlined,
} from '@ant-design/icons-vue'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const errorHandler = useErrorHandler({ showNotification: true })
const { t } = useLanguage()

const selectedKeys = ref<string[]>([route.path])
const showMobileMenu = ref(false)

// Computed drawer title based on current route
const drawerTitle = computed(() => {
  switch (route.path) {
    case '/settings':
      return t('nav.settings')
    case '/main':
    default:
      return t('nav.main')
  }
})

// Update selected keys when route changes
watch(
  () => route.path,
  (newPath) => {
    selectedKeys.value = [newPath]
  }
)

function handleMenuSelect({ key }: { key: string }) {
  router.push(key)
}

function handleMobileMenuSelect({ key }: { key: string }) {
  if (key !== 'logout') {
    router.push(key)
  }
  showMobileMenu.value = false
}

async function handleLogout() {
  try {
    await authStore.logout()
    errorHandler.showSuccess(t('nav.logoutSuccess', 'Logout successful'), t('nav.seeYou', 'See you next time!'))
    router.push('/login')
  } catch (error) {
    errorHandler.handleError(error, 'Logout')
  }
}
</script>

<style scoped>
.navigation-header {
  /* Using glass class from global styles, overriding specific props */
  padding: 0;
  height: 64px;
  line-height: 64px;
  position: sticky;
  top: 0;
  z-index: 999;
  border-bottom: 1px solid var(--border-color);
  background: var(--glass-bg);
  backdrop-filter: blur(10px);
}

.nav-container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 100%;
}

.nav-logo {
  display: flex;
  align-items: center;
  gap: 12px;
  color: var(--text-main);
  font-size: 20px;
  font-weight: 700;
  cursor: pointer;
  transition: opacity 0.3s;
  letter-spacing: -0.5px;
}

.nav-logo:hover {
  opacity: 0.8;
}

.logo-icon {
  width: 32px;
  height: 32px;
  flex-shrink: 0;
  filter: drop-shadow(0 2px 4px rgba(99, 102, 241, 0.3));
}

.logo-text {
  background: -webkit-linear-gradient(45deg, var(--primary-color), var(--secondary-color));
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

/* Desktop Menu Styles to Override Ant Design Default */
.nav-menu {
  flex: 1;
  margin: 0 48px;
  background: transparent;
  border-bottom: none;
  display: flex;
  align-items: center;
}

.nav-menu :deep(.ant-menu-item) {
  color: var(--text-secondary);
  font-weight: 500;
  margin: 0 8px;
  border-radius: 24px;
  transition: all 0.3s;
  height: 48px;
  line-height: 48px;
  padding: 0 20px;
  display: flex;
  align-items: center;
}

.nav-menu :deep(.ant-menu-item:hover) {
  color: var(--primary-color);
  background: var(--item-hover-bg);
}

.nav-menu :deep(.ant-menu-item-selected) {
  color: var(--primary-color);
  background: rgba(99, 102, 241, 0.1); /* Primary color with low opacity */
}

/* User Section */
.nav-user {
  display: flex;
  align-items: center;
  gap: 16px;
}

.user-button {
  color: var(--text-main);
  display: flex;
  align-items: center;
  gap: 10px;
  height: 48px;
  padding: 0 12px;
  border-radius: 24px; /* Pill shape */
  transition: all 0.3s;
  border: 1px solid transparent;
}

.user-button:hover {
  background: var(--item-hover-bg);
  border-color: transparent;
}

.user-avatar {
  background-color: var(--primary-color);
  color: white;
  font-weight: 600;
}

.username {
  font-weight: 500;
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dropdown-icon {
  font-size: 10px;
  color: var(--text-secondary);
}

/* Mobile Menu Button */
.mobile-menu-button {
  display: none;
  color: var(--text-main);
  font-size: 20px;
  height: 40px;
  width: 40px;
  border-radius: 8px;
  transition: all 0.3s;
}

.mobile-menu-button:hover {
  background: rgba(0, 0, 0, 0.05);
  color: var(--primary-color);
}

/* Mobile Styles */
@media (max-width: 768px) {
  .logo-text {
    display: none;
  }
  
  .desktop-menu, .nav-user {
    display: none;
  }
  
  .mobile-menu-button {
    display: flex;
    align-items: center;
    justify-content: center;
  }
  
  .nav-container {
    padding: 0 16px;
  }
}

/* Drawer Content Styles */
.mobile-drawer-content {
  display: flex;
  flex-direction: column;
}

.mobile-user-info {
  padding: 16px;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(139, 92, 246, 0.1));
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 12px;
  border-radius: 12px;
}

.mobile-username {
  font-weight: 600;
  font-size: 15px;
  color: var(--text-main);
}

.mobile-controls {
  padding: 0 16px;
  margin-bottom: 8px;
}

.control-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid var(--border-color);
}

.control-label {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
}

.mobile-controls :deep(.theme-toggle-btn) {
  width: 32px;
  height: 32px;
}

.mobile-controls :deep(.theme-icon) {
  font-size: 18px;
}

.mobile-nav-menu {
  border: none;
  border-inline-end: none !important; /* Remove the vertical line on the right */
  background: transparent !important; /* Remove unified white background */
  margin-top: 4px;
}

.mobile-nav-menu :deep(.ant-menu-item) {
  height: 44px;
  line-height: 44px;
  margin: 2px 12px;
  width: auto;
  border-radius: 8px;
  padding: 0 16px;
}

.mobile-nav-menu :deep(.ant-menu-item-selected) {
  background-color: rgba(99, 102, 241, 0.08); /* Indigo 50 opacity */
  color: var(--primary-color);
}

.danger-item {
  color: var(--error-color);
}
</style>
