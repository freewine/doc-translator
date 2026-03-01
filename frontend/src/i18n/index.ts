import { createI18n } from 'vue-i18n'
import zh from './locales/zh'
import vi from './locales/vi'
import en from './locales/en'

// Get saved language preference or default to English
const savedLanguage = localStorage.getItem('ui_language') || 'en'

const i18n = createI18n({
  legacy: false, // Use Composition API mode
  locale: savedLanguage,
  fallbackLocale: 'en',
  messages: {
    zh,
    vi,
    en
  }
})

export default i18n
