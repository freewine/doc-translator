<template>
  <div class="change-password-page">
    <div class="background-shapes">
      <div class="shape shape-1"></div>
      <div class="shape shape-2"></div>
    </div>

    <div class="page-header-tools">
      <ThemeSwitcher class="theme-switch" />
      <LanguageSwitcher />
    </div>

    <a-card class="password-card glass-card" :bordered="false">
      <template #title>
        <div class="card-title">
          <LockOutlined class="title-icon" />
          <span>{{ t('changePassword.title') }}</span>
        </div>
      </template>

      <a-form
        ref="formRef"
        :model="formData"
        :rules="rules"
        layout="vertical"
        class="password-form"
        @finish="handleSubmit"
      >
        <div class="instruction-text">
          <p>{{ t('changePassword.subtitle') }}</p>
        </div>

        <a-form-item :label="t('changePassword.currentPassword')" name="currentPassword" has-feedback>
          <a-input-password
            v-model:value="formData.currentPassword"
            size="large"
            :placeholder="t('changePassword.currentPasswordPlaceholder', '请输入当前密码')"
            class="modern-input"
            :disabled="loading"
          >
            <template #prefix>
              <LockOutlined class="input-icon" />
            </template>
          </a-input-password>
        </a-form-item>

        <a-form-item :label="t('changePassword.newPassword')" name="newPassword" has-feedback>
          <a-input-password
            v-model:value="formData.newPassword"
            size="large"
            :placeholder="t('changePassword.newPasswordPlaceholder', '请输入新密码')"
            class="modern-input"
            :disabled="loading"
          >
            <template #prefix>
              <LockOutlined class="input-icon" />
            </template>
          </a-input-password>
          <PasswordStrengthIndicator
            v-if="formData.newPassword"
            :password="formData.newPassword"
          />
        </a-form-item>

        <a-form-item :label="t('changePassword.confirmPassword')" name="confirmPassword" has-feedback>
          <a-input-password
            v-model:value="formData.confirmPassword"
            size="large"
            :placeholder="t('changePassword.confirmPasswordPlaceholder', '请再次输入新密码')"
            class="modern-input"
            :disabled="loading"
          >
            <template #prefix>
              <LockOutlined class="input-icon" />
            </template>
          </a-input-password>
        </a-form-item>

        <a-form-item class="submit-item">
          <a-button
            type="primary"
            html-type="submit"
            size="large"
            block
            :loading="loading"
            class="submit-button"
          >
            {{ t('changePassword.submit') }}
          </a-button>
        </a-form-item>
      </a-form>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import type { FormInstance, Rule } from 'ant-design-vue/es/form'
import { LockOutlined } from '@ant-design/icons-vue'
import { useLanguage } from '@/composables/useLanguage'
import { useAuthStore } from '@/stores/auth'
import PasswordStrengthIndicator from '@/components/PasswordStrengthIndicator.vue'
import LanguageSwitcher from '@/components/LanguageSwitcher.vue'
import ThemeSwitcher from '@/components/ThemeSwitcher.vue'
import type { ChangePasswordData } from '@/types'

const { t } = useLanguage()
const router = useRouter()
const authStore = useAuthStore()

const formRef = ref<FormInstance>()
const loading = ref(false)

const formData = ref<ChangePasswordData>({
  currentPassword: '',
  newPassword: '',
  confirmPassword: '',
})

const rules: Record<string, Rule[]> = {
  currentPassword: [
    { required: true, message: t('validation.required') },
  ],
  newPassword: [
    { required: true, message: t('validation.required') },
    { min: 6, message: t('userManagement.passwordMinLength', '密码至少6个字符') },
  ],
  confirmPassword: [
    { required: true, message: t('validation.required') },
    {
      validator: async (_rule: Rule, value: string) => {
        if (value && value !== formData.value.newPassword) {
          throw new Error(t('changePassword.errors.passwordMismatch'))
        }
      },
    },
  ],
}

async function handleSubmit() {
  try {
    await formRef.value?.validate()
    loading.value = true

    const success = await authStore.changePassword({
      currentPassword: formData.value.currentPassword,
      newPassword: formData.value.newPassword,
    })

    if (success) {
      message.success(t('changePassword.success'))
      // Wait for Vue reactivity to propagate state change before navigating
      await nextTick()
      await router.push('/main')
    }
  } catch (error: any) {
    const errorMsg = error.message || ''
    if (errorMsg.includes('INVALID_CURRENT_PASSWORD') || errorMsg.includes('Invalid current password') || errorMsg.includes('incorrect')) {
      message.error(t('changePassword.errors.invalidCurrentPassword'))
    } else if (errorMsg.includes('PASSWORD_SAME_AS_OLD') || errorMsg.includes('same as old') || errorMsg.includes('same as the initial')) {
      message.error(t('changePassword.errors.passwordSameAsOld'))
    } else {
      message.error(errorMsg || t('error.unknown'))
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.change-password-page {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background-color: var(--bg-color);
  background: var(--login-bg-gradient);
  padding: 20px;
  position: relative;
  overflow: hidden;
}

/* Background Shapes (Consistent with LoginPage) */
.background-shapes {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 0;
  overflow: hidden;
  pointer-events: none;
}

.shape {
  position: absolute;
  filter: blur(80px);
  opacity: 0.6;
}

.shape-1 {
  top: -10%;
  left: -10%;
  width: 500px;
  height: 500px;
  background: var(--primary-color);
  border-radius: 50%;
  animation: float 20s infinite ease-in-out;
  opacity: 0.2;
}

.shape-2 {
  bottom: -10%;
  right: -10%;
  width: 600px;
  height: 600px;
  background: var(--secondary-color);
  border-radius: 50%;
  animation: float 25s infinite ease-in-out reverse;
  opacity: 0.2;
}

@keyframes float {
  0% { transform: translate(0, 0) rotate(0deg); }
  50% { transform: translate(30px, 30px) rotate(10deg); }
  100% { transform: translate(0, 0) rotate(0deg); }
}

.page-header-tools {
  position: absolute;
  top: 24px;
  right: 24px;
  z-index: 10;
  display: flex;
  align-items: center;
  gap: 12px;
}

.password-card {
  width: 100%;
  max-width: 480px;
  z-index: 1;
  border: none;
  /* Glassmorphism handled by global glass-card class */
}

.card-title {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  font-size: 24px;
  font-weight: 700;
  color: var(--primary-color);
  padding: 16px 0 8px;
}

.title-icon {
  font-size: 28px;
}

.instruction-text {
  text-align: center;
  margin-bottom: 24px;
  color: var(--text-secondary);
}

.instruction-text p {
  margin: 0;
}

.modern-input {
  border-radius: 8px;
  padding: 8px 11px;
}

.input-icon {
  color: var(--text-secondary);
}

.password-form :deep(.ant-form-item-label > label) {
  color: var(--text-secondary);
  font-weight: 500;
}

.submit-item {
  margin-top: 32px;
  margin-bottom: 12px;
}

.submit-button {
  height: 48px;
  font-size: 16px;
  font-weight: 600;
  border-radius: 8px;
  background: linear-gradient(135deg, var(--primary-color), var(--primary-hover));
  border: none;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
  transition: all 0.3s;
}

.submit-button:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(99, 102, 241, 0.4);
}

/* Mobile optimizations */
@media (max-width: 576px) {
  .password-card {
    max-width: 100%;
    margin: 0 16px;
  }
}
</style>
