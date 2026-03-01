<template>
  <div class="login-page">
    <div class="login-background-shapes">
      <div class="shape shape-1"></div>
      <div class="shape shape-2"></div>
    </div>
    
    <div class="login-header">
      <ThemeSwitcher class="theme-switch" />
      <LanguageSwitcher />
    </div>
    <a-card class="login-card glass-card" :bordered="false">
      <template #title>
        <div class="card-title">
          <FileTextOutlined class="title-icon" />
          <span>{{ t('app.title') }}</span>
        </div>
      </template>
      
      <a-form
        :model="formState"
        :rules="rules"
        layout="vertical"
        @finish="handleSubmit"
        @finishFailed="handleSubmitFailed"
        class="login-form"
      >
        <div class="welcome-text">
          <h3>{{ t('login.welcome', 'Welcome Back') }}</h3>
          <p>{{ t('login.welcomeSubtitle', 'Please enter your details to sign in.') }}</p>
        </div>

        <a-form-item :label="t('login.username')" name="username" has-feedback>
          <a-input
            v-model:value="formState.username"
            :placeholder="t('login.username')"
            size="large"
            :disabled="authStore.isLoading"
            @pressEnter="handleSubmit"
            class="modern-input"
          >
            <template #prefix>
              <UserOutlined class="input-icon" />
            </template>
          </a-input>
        </a-form-item>

        <a-form-item :label="t('login.password')" name="password" has-feedback>
          <a-input-password
            v-model:value="formState.password"
            :placeholder="t('login.password')"
            size="large"
            :disabled="authStore.isLoading"
            @pressEnter="handleSubmit"
            class="modern-input"
          >
            <template #prefix>
              <LockOutlined class="input-icon" />
            </template>
          </a-input-password>
        </a-form-item>

        <a-alert
          v-if="authStore.error"
          :message="t('login.error')"
          type="error"
          show-icon
          closable
          @close="authStore.clearError"
          class="error-alert"
        />

        <a-form-item class="submit-item">
          <a-button
            type="primary"
            html-type="submit"
            size="large"
            block
            :loading="authStore.isLoading"
            class="submit-button"
          >
            {{ authStore.isLoading ? t('login.submitting') : t('login.submit') }}
          </a-button>
        </a-form-item>
      </a-form>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useErrorHandler } from '@/composables/useErrorHandler'
import { useLanguage } from '@/composables/useLanguage'
import LanguageSwitcher from '@/components/LanguageSwitcher.vue'
import ThemeSwitcher from '@/components/ThemeSwitcher.vue'
import { UserOutlined, LockOutlined, FileTextOutlined } from '@ant-design/icons-vue'
import type { Rule } from 'ant-design-vue/es/form'

const router = useRouter()
const authStore = useAuthStore()
const errorHandler = useErrorHandler({ showNotification: true })
const { t } = useLanguage()

interface FormState {
  username: string
  password: string
}

const formState = reactive<FormState>({
  username: '',
  password: '',
})

const rules = computed<Record<string, Rule[]>>(() => ({
  username: [
    { required: true, message: t('login.required', { field: t('login.username') }), trigger: 'blur' },
    { min: 3, message: t('validation.tooShort'), trigger: 'blur' },
    { max: 50, message: t('validation.tooLong'), trigger: 'blur' },
  ],
  password: [
    { required: true, message: t('login.required', { field: t('login.password') }), trigger: 'blur' },
    { min: 6, message: t('validation.tooShort'), trigger: 'blur' },
    { max: 100, message: t('validation.tooLong'), trigger: 'blur' },
  ],
}))

async function handleSubmit() {
  try {
    const result = await authStore.login(formState.username, formState.password)

    if (result.success) {
      errorHandler.showSuccess(t('login.success', 'Login successful'), t('login.welcomeBack', 'Welcome back!'))

      // Redirect to password change page if user must change password
      if (result.mustChangePassword) {
        router.push('/change-password')
      } else {
        router.push('/main')
      }
    }
  } catch (error) {
    errorHandler.handleError(error, 'Login')
  }
}

function handleSubmitFailed(errorInfo: any) {
  console.log('Form validation failed:', errorInfo)
}

// Check if already authenticated on mount
onMounted(() => {
  if (authStore.isAuthenticated) {
    router.push('/main')
  }
})
</script>

<style scoped>
.login-page {
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

/* Abstract Shapes */
.login-background-shapes {
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

.login-header {
  position: absolute;
  top: 24px;
  right: 24px;
  z-index: 10;
  display: flex;
  align-items: center;
  gap: 12px;
}

.login-card {
  width: 100%;
  max-width: 440px;
  z-index: 1;
  /* Glassmorphism handled by global class class-card */
  border: none;
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

.welcome-text {
  text-align: center;
  margin-bottom: 32px;
}

.welcome-text h3 {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-main);
  margin-bottom: 8px;
}

.welcome-text p {
  color: var(--text-secondary);
  margin: 0;
}

.login-form :deep(.ant-form-item-label > label) {
  color: var(--text-secondary);
  font-weight: 500;
}

.modern-input {
  border-radius: 8px;
  padding: 8px 11px;
}

.input-icon {
  color: var(--text-secondary);
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

.error-alert {
  margin-bottom: 24px;
  border-radius: 8px;
}

/* Mobile optimizations */
@media (max-width: 576px) {
  .login-card {
    max-width: 100%;
    margin: 0 16px;
  }
}
</style>
