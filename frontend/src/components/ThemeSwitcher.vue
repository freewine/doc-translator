<template>
  <a-button 
    type="text" 
    class="theme-toggle-btn" 
    @click="toggleTheme"
    :title="isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode'"
  >
    <template #icon>
      <Transition name="fade-scale" mode="out-in">
        <!-- If Dark (show Light option): BulbOutlined -->
        <BulbOutlined v-if="isDark" key="light" class="theme-icon sun-icon" />
        <!-- If Light (show Dark option): BulbFilled -->
        <BulbFilled v-else key="dark" class="theme-icon moon-icon" />
      </Transition>
    </template>
  </a-button>
</template>

<script setup lang="ts">
import { BulbOutlined, BulbFilled } from '@ant-design/icons-vue'
import { useTheme } from '@/composables/useTheme'

const { isDark, toggleTheme } = useTheme()
</script>

<style scoped>
.theme-toggle-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  transition: all 0.3s ease;
  color: var(--text-main);
}

.theme-toggle-btn:hover {
  background: rgba(0, 0, 0, 0.05);
  color: var(--primary-color);
}

[data-theme='dark'] .theme-toggle-btn:hover {
  background: rgba(255, 255, 255, 0.1);
}

.theme-icon {
  font-size: 20px;
}

.sun-icon {
  color: #f59e0b; /* Amber for Light/Sun representation */
}

.moon-icon {
  color: #6366f1; /* Indigo for Dark/Moon representation */
}

/* Animations */
.fade-scale-enter-active,
.fade-scale-leave-active {
  transition: all 0.2s ease;
}

.fade-scale-enter-from {
  opacity: 0;
  transform: scale(0.5) rotate(-90deg);
}

.fade-scale-leave-to {
  opacity: 0;
  transform: scale(0.5) rotate(90deg);
}
</style>
