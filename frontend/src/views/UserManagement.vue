<template>
  <div class="user-management-page">
    <div class="page-header">
      <div class="header-content">
        <h1 class="page-title">{{ t('userManagement.title') }}</h1>
        <p class="page-subtitle">{{ t('userManagement.subtitle', '管理系统用户账户') }}</p>
      </div>
      <a-button type="primary" @click="showCreateDialog">
        <PlusOutlined />
        {{ t('userManagement.createUser') }}
      </a-button>
    </div>

    <a-spin :spinning="userStore.isLoading">
      <a-row :gutter="[16, 16]" v-if="userStore.users.length > 0">
        <a-col
          v-for="user in userStore.users"
          :key="user.username"
          :xs="24"
          :sm="12"
          :md="8"
          :lg="6"
        >
          <UserCard
            :user="user"
            :is-current="user.username === authStore.user?.username"
            @edit="showEditDialog"
            @delete="confirmDelete"
            @unlock="handleUnlock"
          />
        </a-col>
      </a-row>

      <a-empty v-else-if="!userStore.isLoading" :description="t('userManagement.noUsers', '暂无用户')">
        <a-button type="primary" @click="showCreateDialog">
          <PlusOutlined />
          {{ t('userManagement.createUser') }}
        </a-button>
      </a-empty>
    </a-spin>

    <UserEditDialog
      v-model:visible="dialogVisible"
      :user="editingUser"
      @create="handleCreate"
      @update="handleUpdate"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Modal, message } from 'ant-design-vue'
import { PlusOutlined } from '@ant-design/icons-vue'
import { useLanguage } from '@/composables/useLanguage'
import { useAuthStore } from '@/stores/auth'
import { useUserStore } from '@/stores/user'
import UserCard from '@/components/UserCard.vue'
import UserEditDialog from '@/components/UserEditDialog.vue'
import type { User, UserRole } from '@/types'

const { t } = useLanguage()
const authStore = useAuthStore()
const userStore = useUserStore()

const dialogVisible = ref(false)
const editingUser = ref<User | null>(null)

onMounted(() => {
  userStore.fetchUsers()
})

function showCreateDialog() {
  editingUser.value = null
  dialogVisible.value = true
}

function showEditDialog(user: User) {
  editingUser.value = user
  dialogVisible.value = true
}

function confirmDelete(username: string) {
  const user = userStore.users.find(u => u.username === username)
  if (!user) return

  Modal.confirm({
    title: t('userManagement.deleteUser'),
    content: t('userManagement.confirmDelete', { username: user.username }),
    okText: t('common.delete'),
    okType: 'danger',
    cancelText: t('common.cancel'),
    async onOk() {
      try {
        await userStore.deleteUser(username)
        message.success(t('userManagement.deleteSuccess', '用户删除成功'))
      } catch (error: any) {
        message.error(error.message || t('userManagement.deleteError', '删除失败'))
      }
    },
  })
}

async function handleCreate(data: { username: string; password: string; role: UserRole }) {
  try {
    await userStore.createUser({
      username: data.username,
      password: data.password,
      role: data.role,
    })
    message.success(t('userManagement.createSuccess', '用户创建成功'))
    dialogVisible.value = false
  } catch (error: any) {
    const errorMsg = error.message || ''
    if (errorMsg.includes('already exists') || errorMsg.includes('USER_ALREADY_EXISTS')) {
      message.error(t('userManagement.errors.userAlreadyExists'))
    } else {
      message.error(errorMsg || t('userManagement.createError', '创建失败'))
    }
  }
}

async function handleUpdate(data: { username: string; password?: string; role?: UserRole }) {
  try {
    await userStore.updateUser(data.username, {
      password: data.password,
      role: data.role,
    })
    message.success(t('userManagement.updateSuccess', '用户更新成功'))
    dialogVisible.value = false
  } catch (error: any) {
    message.error(error.message || t('userManagement.updateError', '更新失败'))
  }
}

async function handleUnlock(username: string) {
  try {
    await userStore.unlockUser(username)
    message.success(t('userManagement.unlockSuccess', '用户解锁成功'))
  } catch (error: any) {
    message.error(error.message || t('userManagement.unlockError', '解锁失败'))
  }
}
</script>

<style scoped>
.user-management-page {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
  flex-wrap: wrap;
  gap: 16px;
}

.header-content {
  flex: 1;
  min-width: 200px;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-main);
  margin: 0 0 4px 0;
}

.page-subtitle {
  font-size: 14px;
  color: var(--text-secondary);
  margin: 0;
}

@media (max-width: 576px) {
  .user-management-page {
    padding: 16px;
  }

  .page-header {
    flex-direction: column;
    align-items: stretch;
  }

  .page-header .ant-btn {
    width: 100%;
  }
}
</style>
