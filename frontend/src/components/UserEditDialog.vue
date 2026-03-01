<template>
  <a-modal
    :open="visible"
    :title="isEditMode ? t('userManagement.editUser') : t('userManagement.createUser')"
    :confirm-loading="loading"
    @ok="handleSubmit"
    @cancel="handleCancel"
    :ok-text="t('common.save')"
    :cancel-text="t('common.cancel')"
  >
    <a-form
      ref="formRef"
      :model="formData"
      :rules="rules"
      layout="vertical"
      class="user-form"
    >
      <a-form-item :label="t('userManagement.username')" name="username">
        <a-input
          v-model:value="formData.username"
          :placeholder="t('userManagement.usernamePlaceholder', '请输入用户名')"
          :disabled="isEditMode"
        />
      </a-form-item>

      <a-form-item :label="t('userManagement.password')" name="password">
        <a-input-password
          v-model:value="formData.password"
          :placeholder="isEditMode
            ? t('userManagement.passwordEditPlaceholder', '留空表示不修改')
            : t('userManagement.passwordPlaceholder', '请输入密码')"
        />
        <PasswordStrengthIndicator
          v-if="formData.password"
          :password="formData.password"
        />
      </a-form-item>

      <a-form-item :label="t('userManagement.confirmPassword')" name="confirmPassword">
        <a-input-password
          v-model:value="formData.confirmPassword"
          :placeholder="t('userManagement.confirmPasswordPlaceholder', '请再次输入密码')"
        />
      </a-form-item>

      <a-form-item :label="t('userManagement.role')" name="role">
        <a-select
          v-model:value="formData.role"
          :disabled="!canEditRole"
        >
          <a-select-option value="admin">
            {{ t('userManagement.roles.admin') }}
          </a-select-option>
          <a-select-option value="user">
            {{ t('userManagement.roles.user') }}
          </a-select-option>
        </a-select>
        <div v-if="!canEditRole" class="role-hint">
          {{ t('userManagement.cannotChangeOwnRole') }}
        </div>
      </a-form-item>
    </a-form>
  </a-modal>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import type { FormInstance, Rule } from 'ant-design-vue/es/form'
import { useLanguage } from '@/composables/useLanguage'
import { usePermission } from '@/composables/usePermission'
import PasswordStrengthIndicator from './PasswordStrengthIndicator.vue'
import type { User, UserFormData, UserRole } from '@/types'

const props = defineProps<{
  visible: boolean
  user?: User | null
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  saved: [user: User]
  create: [data: { username: string; password: string; role: UserRole }]
  update: [data: { username: string; password?: string; role?: UserRole }]
}>()

const { t } = useLanguage()
const { canEditUserRole } = usePermission()

const formRef = ref<FormInstance>()
const loading = ref(false)

const formData = ref<UserFormData>({
  username: '',
  password: '',
  confirmPassword: '',
  role: 'user',
})

const isEditMode = computed(() => !!props.user)

const canEditRole = computed(() => {
  if (!props.user?.username) return true
  return canEditUserRole(props.user.username)
})

// Validation rules
const rules = computed<Record<string, Rule[]>>(() => ({
  username: [
    { required: !isEditMode.value, message: t('validation.required') },
    { min: 3, max: 50, message: t('userManagement.usernameLength', '用户名长度3-50字符') },
    { pattern: /^[a-zA-Z0-9_]+$/, message: t('userManagement.usernameFormat', '只允许字母、数字、下划线') },
  ],
  password: [
    { required: !isEditMode.value, message: t('validation.required') },
    { min: 6, message: t('userManagement.passwordMinLength', '密码至少6个字符') },
  ],
  confirmPassword: [
    { required: !!formData.value.password, message: t('validation.required') },
    {
      validator: async (_rule: Rule, value: string) => {
        if (formData.value.password && value !== formData.value.password) {
          throw new Error(t('changePassword.errors.passwordMismatch'))
        }
      },
    },
  ],
  role: [
    { required: true, message: t('validation.required') },
  ],
}))

// Watch for user prop changes to populate form
watch(
  () => props.user,
  (newUser) => {
    if (newUser) {
      formData.value = {
        username: newUser.username,
        password: '',
        confirmPassword: '',
        role: newUser.role || 'user',
      }
    } else {
      formData.value = {
        username: '',
        password: '',
        confirmPassword: '',
        role: 'user',
      }
    }
  },
  { immediate: true }
)

// Reset form when dialog opens
watch(
  () => props.visible,
  (visible) => {
    if (visible && !props.user) {
      formData.value = {
        username: '',
        password: '',
        confirmPassword: '',
        role: 'user',
      }
      formRef.value?.resetFields()
    }
  }
)

async function handleSubmit() {
  try {
    await formRef.value?.validate()
    loading.value = true

    if (isEditMode.value && props.user?.username) {
      // Update existing user - use username as identifier
      emit('update', {
        username: props.user.username,
        password: formData.value.password || undefined,
        role: canEditRole.value ? formData.value.role : undefined,
      })
    } else {
      // Create new user
      emit('create', {
        username: formData.value.username,
        password: formData.value.password!,
        role: formData.value.role,
      })
    }
  } catch (error) {
    console.error('Form validation failed:', error)
  } finally {
    loading.value = false
  }
}

function handleCancel() {
  emit('update:visible', false)
}
</script>

<style scoped>
.user-form {
  padding-top: 16px;
}

.role-hint {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 4px;
}
</style>
