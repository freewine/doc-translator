<template>
  <a-card class="user-card" :class="{ 'is-current': isCurrent, 'is-deleted': user.status === 'DELETED' }">
    <div class="card-header">
      <a-avatar size="large" :style="{ backgroundColor: avatarColor }">
        {{ avatarLetter }}
      </a-avatar>
      <div class="user-info">
        <div class="username">
          {{ user.username }}
          <a-tag v-if="isCurrent" color="blue" size="small">
            {{ t('userManagement.currentUser') }}
          </a-tag>
        </div>
        <a-tag :color="roleConfig.color">
          {{ t(`userManagement.roles.${(user.role || 'user').toLowerCase()}`) }}
        </a-tag>
      </div>
    </div>

    <div class="card-body">
      <div class="status-row">
        <component :is="statusConfig.icon" :style="{ color: statusConfig.color }" />
        <span :style="{ color: statusConfig.color }">
          {{ t(`userManagement.statuses.${user.status}`) }}
        </span>
      </div>

      <div class="time-row">
        <CalendarOutlined />
        <span>{{ t('userManagement.createdAt') }}: {{ formatDate(user.createdAt) }}</span>
      </div>

      <div v-if="user.failedLoginCount && user.failedLoginCount > 0" class="time-row">
        <LockOutlined />
        <span>{{ t('userManagement.failedLogins', '登录失败') }}: {{ user.failedLoginCount }}</span>
      </div>
    </div>

    <div class="card-actions" v-if="user.status !== 'DELETED'">
      <a-tooltip :title="t('common.edit')">
        <a-button type="text" size="small" @click="$emit('edit', user)">
          <EditOutlined />
        </a-button>
      </a-tooltip>
      <a-tooltip v-if="user.status === 'LOCKED'" :title="t('userManagement.unlock')">
        <a-button type="text" size="small" @click="$emit('unlock', user.username)">
          <UnlockOutlined />
        </a-button>
      </a-tooltip>
      <a-tooltip :title="t('common.delete')">
        <a-button
          type="text"
          size="small"
          danger
          :disabled="isCurrent"
          @click="$emit('delete', user.username)"
        >
          <DeleteOutlined />
        </a-button>
      </a-tooltip>
    </div>
  </a-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useLanguage } from '@/composables/useLanguage'
import type { User } from '@/types'
import { UserStatus } from '@/types'
import {
  EditOutlined,
  DeleteOutlined,
  UnlockOutlined,
  CalendarOutlined,
  KeyOutlined,
  CheckCircleOutlined,
  LockOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons-vue'

const props = defineProps<{
  user: User
  isCurrent?: boolean
}>()

defineEmits<{
  edit: [user: User]
  delete: [username: string]
  unlock: [username: string]
}>()

const { t } = useLanguage()

const avatarLetter = computed(() => {
  return (props.user.username || 'U').charAt(0).toUpperCase()
})

const normalizedRole = computed(() => (props.user.role || 'user').toLowerCase())

const avatarColor = computed(() => {
  return normalizedRole.value === 'admin' ? '#722ed1' : '#1890ff'
})

const roleConfig = computed((): { color: string } => {
  const configs: Record<string, { color: string }> = {
    admin: { color: 'purple' },
    user: { color: 'blue' },
  }
  return configs[normalizedRole.value] ?? { color: 'blue' }
})

const statusConfig = computed((): { icon: any; color: string } => {
  const configs: Record<string, { icon: any; color: string }> = {
    PENDING_PASSWORD: { icon: KeyOutlined, color: '#fa8c16' },
    ACTIVE: { icon: CheckCircleOutlined, color: '#52c41a' },
    LOCKED: { icon: LockOutlined, color: '#f5222d' },
    DELETED: { icon: CloseCircleOutlined, color: '#8c8c8c' },
  }
  return configs[props.user.status || 'ACTIVE'] ?? { icon: CheckCircleOutlined, color: '#52c41a' }
})

function formatDate(dateStr?: string): string {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}
</script>

<style scoped>
.user-card {
  border-radius: 12px;
  transition: all 0.3s ease;
  border: 1px solid var(--border-color);
}

.user-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.user-card.is-current {
  border-color: var(--primary-color);
  background: rgba(99, 102, 241, 0.02);
}

.user-card.is-deleted {
  opacity: 0.6;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.user-info {
  flex: 1;
  min-width: 0;
}

.username {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-main);
  margin-bottom: 4px;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.card-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.status-row,
.time-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--text-secondary);
}

.card-actions {
  display: flex;
  justify-content: flex-end;
  gap: 4px;
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid var(--border-color);
}
</style>
