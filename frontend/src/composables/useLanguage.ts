import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

export type Language = 'en' | 'zh' | 'vi'

export function useLanguage() {
  const { locale, t } = useI18n()

  const currentLanguage = computed<Language>(() => locale.value as Language)

  const setLanguage = (lang: Language) => {
    locale.value = lang
    localStorage.setItem('ui_language', lang)
    document.documentElement.lang = lang
  }

  const toggleLanguage = () => {
    const languages: Language[] = ['en', 'zh', 'vi']
    const currentIndex = languages.indexOf(currentLanguage.value)
    const nextIndex = (currentIndex + 1) % languages.length
    const nextLang = languages[nextIndex] ?? 'en'
    setLanguage(nextLang)
  }

  const languageOptions = [
    { value: 'en', label: 'English' },
    { value: 'zh', label: '中文' },
    { value: 'vi', label: 'Tiếng Việt' }
  ]

  return {
    currentLanguage,
    setLanguage,
    toggleLanguage,
    languageOptions,
    t
  }
}
