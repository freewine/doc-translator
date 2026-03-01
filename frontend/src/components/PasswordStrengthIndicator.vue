<template>
  <div class="password-strength">
    <div class="strength-bar">
      <div 
        class="strength-fill" 
        :class="strengthClass"
        :style="{ width: strengthWidth }"
      />
    </div>
    <span class="strength-text" :class="strengthClass">
      {{ strengthText }}
    </span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useLanguage } from '@/composables/useLanguage'
import { PasswordStrength } from '@/types'

const props = defineProps<{
  password: string
}>()

const { t } = useLanguage()

const strength = computed((): PasswordStrength => {
  const pwd = props.password || ''
  
  if (pwd.length < 8) {
    return PasswordStrength.WEAK
  }
  
  const hasLetter = /[a-zA-Z]/.test(pwd)
  const hasNumber = /\d/.test(pwd)
  const hasUpper = /[A-Z]/.test(pwd)
  const hasLower = /[a-z]/.test(pwd)
  
  if (pwd.length >= 10 && hasUpper && hasLower && hasNumber) {
    return PasswordStrength.STRONG
  }
  
  if (hasLetter && hasNumber) {
    return PasswordStrength.MEDIUM
  }
  
  return PasswordStrength.WEAK
})

const strengthClass = computed(() => {
  return `strength-${strength.value}`
})

const strengthWidth = computed(() => {
  switch (strength.value) {
    case PasswordStrength.WEAK:
      return '33%'
    case PasswordStrength.MEDIUM:
      return '66%'
    case PasswordStrength.STRONG:
      return '100%'
    default:
      return '0%'
  }
})

const strengthText = computed(() => {
  return t(`changePassword.strength.${strength.value}`)
})
</script>

<style scoped>
.password-strength {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 4px;
}

.strength-bar {
  flex: 1;
  height: 6px;
  background: var(--border-color);
  border-radius: 3px;
  overflow: hidden;
}

.strength-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.3s ease, background-color 0.3s ease;
}

.strength-fill.strength-weak {
  background: var(--error-color);
}

.strength-fill.strength-medium {
  background: var(--warning-color);
}

.strength-fill.strength-strong {
  background: var(--success-color);
}

.strength-text {
  font-size: 12px;
  font-weight: 500;
  min-width: 24px;
}

.strength-text.strength-weak {
  color: var(--error-color);
}

.strength-text.strength-medium {
  color: var(--warning-color);
}

.strength-text.strength-strong {
  color: var(--success-color);
}
</style>
