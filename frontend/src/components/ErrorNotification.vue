<template>
  <div class="error-notification-container">
    <!-- This component uses Ant Design Vue's notification system -->
    <!-- Notifications are shown programmatically via the useErrorHandler composable -->
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { notification } from 'ant-design-vue'

// Configure global notification settings
onMounted(() => {
  notification.config({
    placement: 'topRight',
    top: '70px',
    duration: 4.5,
    maxCount: 3,
  })
})

// Clean up on unmount
onUnmounted(() => {
  notification.destroy()
})
</script>

<style scoped>
.error-notification-container {
  /* This component doesn't render anything visible */
  /* It just configures the notification system */
  display: none;
}
</style>
