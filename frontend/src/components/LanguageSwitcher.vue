<template>
  <a-select
    v-model:value="currentLanguage"
    :options="languageOptions"
    @change="handleLanguageChange"
    style="width: 120px"
    size="small"
  >
    <template #suffixIcon>
      <GlobalOutlined />
    </template>
  </a-select>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { GlobalOutlined } from '@ant-design/icons-vue'
import { useLanguage, type Language } from '../composables/useLanguage'

const { currentLanguage: lang, setLanguage, languageOptions } = useLanguage()

const currentLanguage = computed({
  get: () => lang.value,
  set: (value: Language) => setLanguage(value)
})

const handleLanguageChange = (value: Language) => {
  setLanguage(value)
}
</script>

<style scoped>
/* Component-specific styles if needed */
</style>
