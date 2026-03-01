import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { LanguagePair, ModelInfo, ModelConfig } from '@/types'

const LANGUAGE_PAIRS_KEY = 'language_pairs'
const SETTINGS_KEY = 'app_settings'
const MODEL_CONFIG_KEY = 'model_config'

export interface AppSettings {
  pollIntervalMs: number
  maxFileSize: number
  theme: 'light' | 'dark' | 'auto'
  language: 'en' | 'zh' | 'vi'
}

const DEFAULT_SETTINGS: AppSettings = {
  pollIntervalMs: 2000,
  maxFileSize: 50 * 1024 * 1024, // 50MB
  theme: 'auto',
  language: 'en',
}

export const useConfigStore = defineStore('config', () => {
  const languagePairs = ref<LanguagePair[]>([])
  const settings = ref<AppSettings>({ ...DEFAULT_SETTINGS })
  const modelConfig = ref<ModelConfig | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  // Computed properties
  const hasLanguagePairs = computed(() => languagePairs.value.length > 0)
  
  const getLanguagePairById = computed(() => (id: string) => 
    languagePairs.value.find((pair: LanguagePair) => pair.id === id)
  )
  
  const availableModels = computed(() => modelConfig.value?.availableModels || [])
  
  const currentModel = computed(() => ({
    modelId: modelConfig.value?.modelId || '',
    modelName: modelConfig.value?.modelName || ''
  }))

  /**
   * Set language pairs
   */
  function setLanguagePairs(pairs: LanguagePair[]) {
    // Create a shallow copy to avoid frozen arrays from Apollo Client
    languagePairs.value = [...pairs]
    persistLanguagePairs()
  }

  /**
   * Add a language pair
   */
  function addLanguagePair(pair: LanguagePair) {
    // Check for duplicates
    const exists = languagePairs.value.some(
      (p: LanguagePair) => 
        p.sourceLanguageCode === pair.sourceLanguageCode && 
        p.targetLanguageCode === pair.targetLanguageCode
    )

    if (exists) {
      error.value = 'Language pair already exists'
      return false
    }

    languagePairs.value.push(pair)
    persistLanguagePairs()
    return true
  }

  /**
   * Update a language pair
   */
  function updateLanguagePair(id: string, updates: Partial<LanguagePair>): boolean {
    const index = languagePairs.value.findIndex((pair: LanguagePair) => pair.id === id)
    if (index !== -1) {
      const currentPair = languagePairs.value[index]
      if (currentPair) {
        languagePairs.value[index] = {
          id: currentPair.id,
          sourceLanguage: updates.sourceLanguage ?? currentPair.sourceLanguage,
          targetLanguage: updates.targetLanguage ?? currentPair.targetLanguage,
          sourceLanguageCode: updates.sourceLanguageCode ?? currentPair.sourceLanguageCode,
          targetLanguageCode: updates.targetLanguageCode ?? currentPair.targetLanguageCode,
        }
        persistLanguagePairs()
        return true
      }
    }
    return false
  }

  /**
   * Remove a language pair
   */
  function removeLanguagePair(id: string) {
    const initialLength = languagePairs.value.length
    languagePairs.value = languagePairs.value.filter((pair: LanguagePair) => pair.id !== id)
    
    if (languagePairs.value.length < initialLength) {
      persistLanguagePairs()
      return true
    }
    return false
  }

  /**
   * Update settings
   */
  function updateSettings(newSettings: Partial<AppSettings>) {
    settings.value = { ...settings.value, ...newSettings }
    persistSettings()
  }

  /**
   * Reset settings to defaults
   */
  function resetSettings() {
    settings.value = { ...DEFAULT_SETTINGS }
    persistSettings()
  }

  /**
   * Update poll interval
   */
  function setPollInterval(intervalMs: number) {
    if (intervalMs >= 1000 && intervalMs <= 10000) {
      settings.value.pollIntervalMs = intervalMs
      persistSettings()
    }
  }

  /**
   * Update theme
   */
  function setTheme(theme: 'light' | 'dark' | 'auto') {
    settings.value.theme = theme
    persistSettings()
  }

  /**
   * Update language
   */
  function setLanguage(language: 'en' | 'zh' | 'vi') {
    settings.value.language = language
    persistSettings()
  }

  /**
   * Persist language pairs to localStorage
   */
  function persistLanguagePairs() {
    try {
      const data = JSON.stringify(languagePairs.value)
      localStorage.setItem(LANGUAGE_PAIRS_KEY, data)
    } catch (err) {
      console.error('Failed to persist language pairs:', err)
    }
  }

  /**
   * Persist settings to localStorage
   */
  function persistSettings() {
    try {
      const data = JSON.stringify(settings.value)
      localStorage.setItem(SETTINGS_KEY, data)
    } catch (err) {
      console.error('Failed to persist settings:', err)
    }
  }

  /**
   * Load language pairs from localStorage
   */
  function loadLanguagePairs() {
    try {
      const data = localStorage.getItem(LANGUAGE_PAIRS_KEY)
      if (data) {
        languagePairs.value = JSON.parse(data)
      }
    } catch (err) {
      console.error('Failed to load language pairs:', err)
      languagePairs.value = []
    }
  }

  /**
   * Load settings from localStorage
   */
  function loadSettings() {
    try {
      const data = localStorage.getItem(SETTINGS_KEY)
      if (data) {
        const loadedSettings = JSON.parse(data)
        settings.value = { ...DEFAULT_SETTINGS, ...loadedSettings }
      }
    } catch (err) {
      console.error('Failed to load settings:', err)
      settings.value = { ...DEFAULT_SETTINGS }
    }
  }

  /**
   * Set model configuration
   */
  function setModelConfig(config: ModelConfig) {
    modelConfig.value = config
    persistModelConfig()
  }

  /**
   * Update selected model
   */
  function updateSelectedModel(modelId: string, modelName: string) {
    if (modelConfig.value) {
      modelConfig.value.modelId = modelId
      modelConfig.value.modelName = modelName
      persistModelConfig()
    }
  }

  /**
   * Persist model config to localStorage
   */
  function persistModelConfig() {
    try {
      const data = JSON.stringify(modelConfig.value)
      localStorage.setItem(MODEL_CONFIG_KEY, data)
    } catch (err) {
      console.error('Failed to persist model config:', err)
    }
  }

  /**
   * Load model config from localStorage
   */
  function loadModelConfig() {
    try {
      const data = localStorage.getItem(MODEL_CONFIG_KEY)
      if (data) {
        modelConfig.value = JSON.parse(data)
      }
    } catch (err) {
      console.error('Failed to load model config:', err)
      modelConfig.value = null
    }
  }

  /**
   * Load all config data
   */
  function loadConfig() {
    loadLanguagePairs()
    loadSettings()
    loadModelConfig()
  }

  /**
   * Clear error
   */
  function clearError() {
    error.value = null
  }

  /**
   * Clear all stored data
   */
  function clearAll() {
    languagePairs.value = []
    settings.value = { ...DEFAULT_SETTINGS }
    modelConfig.value = null
    localStorage.removeItem(LANGUAGE_PAIRS_KEY)
    localStorage.removeItem(SETTINGS_KEY)
    localStorage.removeItem(MODEL_CONFIG_KEY)
  }

  return {
    // State
    languagePairs,
    settings,
    modelConfig,
    isLoading,
    error,

    // Computed
    hasLanguagePairs,
    getLanguagePairById,
    availableModels,
    currentModel,

    // Actions
    setLanguagePairs,
    addLanguagePair,
    updateLanguagePair,
    removeLanguagePair,
    updateSettings,
    resetSettings,
    setPollInterval,
    setTheme,
    setLanguage,
    setModelConfig,
    updateSelectedModel,
    loadConfig,
    clearError,
    clearAll,
  }
})
