<template>
  <div class="settings-page">
    <div class="content">
      <div class="page-header">
         <h1><SettingOutlined /> {{ t('nav.settings') }}</h1>
         <p class="subtitle">{{ t('settings.subtitle', 'Manage translation models and language configurations.') }}</p>
      </div>
      
      <a-row :gutter="[24, 24]">
        <!-- Model Selection Card -->
        <a-col :xs="24" :sm="24" :md="24" :lg="24" :xl="24">
          <a-card :bordered="false" :title="t('settings.translationModel', 'Translation Model')" class="settings-card glass-card">
            <template #extra>
               <ExperimentOutlined class="card-icon" />
            </template>
            <a-spin :spinning="isLoadingModel">
              <a-form layout="vertical" class="model-form">
                <a-form-item :label="t('settings.selectModel', 'Select AI Model')">
                  <a-select
                    v-model:value="selectedModelId"
                    size="large"
                    :loading="isUpdatingModel"
                    @change="handleModelChange"
                    class="model-select"
                  >
                    <a-select-option
                      v-for="model in configStore.availableModels"
                      :key="model.id"
                      :value="model.id"
                    >
                      {{ model.name }}
                    </a-select-option>
                  </a-select>
                </a-form-item>
                <div class="current-model-info" v-if="configStore.currentModel.modelName">
                   <InfoCircleOutlined class="info-icon" />
                   <span>{{ t('settings.currentModel', 'Current active model') }}: <strong>{{ configStore.currentModel.modelName }}</strong></span>
                </div>
              </a-form>
            </a-spin>
          </a-card>
        </a-col>

        <!-- Language Pairs Card -->
        <a-col :xs="24" :sm="24" :md="24" :lg="24" :xl="24">
          <a-card :bordered="false" class="settings-card glass-card">
            <template #title>
                <div class="card-header-flex">
                   <span>{{ t('settings.languagePairs') }}</span>
                </div>
            </template>
            <template #extra>
               <GlobalOutlined class="card-icon" />
            </template>
            
            <!-- Add Language Pair Form (admin only) -->
            <div class="inner-section" v-if="canEdit">
              <h3 class="inner-title">{{ t('settings.addLanguagePair') }}</h3>
              <a-form
                :model="formState"
                :rules="formRules"
                layout="vertical"
                @finish="handleAddLanguagePair"
                class="add-pair-form"
              >
                <a-row :gutter="[16, 16]" align="bottom">
                  <a-col :xs="24" :sm="12" :md="12" :lg="5" :xl="5">
                    <a-form-item :label="t('settings.sourceLanguage')" name="sourceLanguage">
                      <a-input
                        v-model:value="formState.sourceLanguage"
                        :placeholder="t('settings.sourceLanguage')"
                        size="large"
                        class="modern-input"
                      />
                    </a-form-item>
                  </a-col>
                  <a-col :xs="24" :sm="12" :md="12" :lg="5" :xl="5">
                    <a-form-item :label="t('settings.sourceCode')" name="sourceLanguageCode">
                      <a-input
                        v-model:value="formState.sourceLanguageCode"
                        :placeholder="t('settings.sourceCode')"
                        :maxlength="5"
                        size="large"
                         class="modern-input"
                      />
                    </a-form-item>
                  </a-col>
                  <a-col :xs="24" :sm="12" :md="12" :lg="5" :xl="5">
                    <a-form-item :label="t('settings.targetLanguage')" name="targetLanguage">
                      <a-input
                        v-model:value="formState.targetLanguage"
                        :placeholder="t('settings.targetLanguage')"
                        size="large"
                         class="modern-input"
                      />
                    </a-form-item>
                  </a-col>
                  <a-col :xs="24" :sm="12" :md="12" :lg="5" :xl="5">
                    <a-form-item :label="t('settings.targetCode')" name="targetLanguageCode">
                      <a-input
                        v-model:value="formState.targetLanguageCode"
                        :placeholder="t('settings.targetCode')"
                        :maxlength="5"
                        size="large"
                         class="modern-input"
                      />
                    </a-form-item>
                  </a-col>
                  <a-col :xs="24" :sm="24" :md="24" :lg="4" :xl="4">
                    <a-form-item class="add-button-form-item">
                      <a-button
                        type="primary"
                        html-type="submit"
                        :loading="isAdding"
                        size="large"
                        block
                        class="add-button"
                      >
                        <template #icon>
                          <PlusOutlined />
                        </template>
                        {{ t('settings.addLanguagePair') }}
                      </a-button>
                    </a-form-item>
                  </a-col>
                </a-row>
              </a-form>
            </div>

            <!-- Language Pairs List -->
            <div class="inner-section list-section">
              <h3 class="inner-title">{{ t('settings.configuredPairs', 'Configured Language Pairs') }}</h3>
              <a-spin :spinning="isLoading">
                <a-empty v-if="!configStore.hasLanguagePairs" :description="t('settings.noLanguagePairs')">
                  <template #image>
                    <GlobalOutlined style="font-size: 48px; color: #d9d9d9;" />
                  </template>
                </a-empty>
                <div v-else class="pairs-grid">
                  <div v-for="item in configStore.languagePairs" :key="item.id" class="pair-card">
                        <div class="pair-content">
                            <div class="pair-visual">
                                 <span class="lang-node source">{{ item.sourceLanguageCode.toUpperCase() }}</span>
                                 <ArrowRightOutlined class="pair-arrow" />
                                 <span class="lang-node target">{{ item.targetLanguageCode.toUpperCase() }}</span>
                            </div>
                            <div class="pair-names">
                                <span>{{ item.sourceLanguage }}</span>
                                <span class="separator">{{ t('common.to', 'to') }}</span>
                                <span>{{ item.targetLanguage }}</span>
                            </div>
                        </div>
                        <a-popconfirm
                          v-if="canEdit"
                          :title="t('settings.confirmDelete', 'Remove this pair?')"
                          :ok-text="t('common.yes')"
                          :cancel-text="t('common.no')"
                          @confirm="handleRemoveLanguagePair(item.id)"
                        >
                          <a-button type="text" danger class="delete-btn" :loading="removingId === item.id">
                            <DeleteOutlined />
                          </a-button>
                        </a-popconfirm>
                  </div>
                </div>
              </a-spin>
            </div>
          </a-card>
        </a-col>
      </a-row>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import {
    GlobalOutlined,
    ArrowRightOutlined,
    PlusOutlined,
    DeleteOutlined,
    SettingOutlined,
    ExperimentOutlined,
    InfoCircleOutlined
} from '@ant-design/icons-vue'
import { useConfigStore } from '@/stores/config'
import { useAuthStore } from '@/stores/auth'
import { useLanguage } from '@/composables/useLanguage'
import { useQuery, useMutation } from '@/composables/useGraphQL'
import {
  ADD_LANGUAGE_PAIR_MUTATION,
  REMOVE_LANGUAGE_PAIR_MUTATION,
  UPDATE_MODEL_MUTATION
} from '@/graphql/mutations'
import { LANGUAGE_PAIRS_QUERY, MODEL_CONFIG_QUERY } from '@/graphql/queries'
import type { LanguagePair, ModelConfig } from '@/types'

const configStore = useConfigStore()
const authStore = useAuthStore()
const { t } = useLanguage()

// Admin-only editing
const canEdit = computed(() => authStore.isAdmin)

// Form state
const formState = reactive({
  sourceLanguage: '',
  targetLanguage: '',
  sourceLanguageCode: '',
  targetLanguageCode: '',
})

// Form validation rules (computed to support i18n)
const formRules = computed(() => ({
  sourceLanguage: [
    { required: true, message: t('settings.validation.sourceLanguageRequired'), trigger: 'blur' },
    { min: 2, message: t('settings.validation.languageNameMinLength'), trigger: 'blur' },
  ],
  targetLanguage: [
    { required: true, message: t('settings.validation.targetLanguageRequired'), trigger: 'blur' },
    { min: 2, message: t('settings.validation.languageNameMinLength'), trigger: 'blur' },
  ],
  sourceLanguageCode: [
    { required: true, message: t('settings.validation.sourceCodeRequired'), trigger: 'blur' },
    { min: 2, max: 5, message: t('settings.validation.codeLength'), trigger: 'blur' },
    { pattern: /^[a-z]{2,5}$/, message: t('settings.validation.codeFormat'), trigger: 'blur' },
  ],
  targetLanguageCode: [
    { required: true, message: t('settings.validation.targetCodeRequired'), trigger: 'blur' },
    { min: 2, max: 5, message: t('settings.validation.codeLength'), trigger: 'blur' },
    { pattern: /^[a-z]{2,5}$/, message: t('settings.validation.codeFormat'), trigger: 'blur' },
  ],
}))

// Loading states
const isLoading = ref(false)
const isAdding = ref(false)
const removingId = ref<string | null>(null)
const isLoadingModel = ref(false)
const isUpdatingModel = ref(false)
const selectedModelId = ref<string>('')

// GraphQL queries and mutations
const { data: languagePairsData, loading: queryLoading, refetch } = useQuery<{ languagePairs: LanguagePair[] }>(LANGUAGE_PAIRS_QUERY)
const { mutate: addLanguagePairMutation } = useMutation<{ addLanguagePair: LanguagePair }>(ADD_LANGUAGE_PAIR_MUTATION)
const { mutate: removeLanguagePairMutation } = useMutation<{ removeLanguagePair: boolean }>(REMOVE_LANGUAGE_PAIR_MUTATION)
const { data: modelConfigData, loading: modelConfigLoading, refetch: refetchModelConfig } = useQuery<{ modelConfig: ModelConfig }>(MODEL_CONFIG_QUERY)
const { mutate: updateModelMutation } = useMutation<{ updateModel: ModelConfig }>(UPDATE_MODEL_MUTATION)

// Load language pairs and model config on mount
onMounted(async () => {
  await Promise.all([
    loadLanguagePairs(),
    loadModelConfig()
  ])
})

// Load language pairs from API
async function loadLanguagePairs() {
  try {
    isLoading.value = true
    await refetch()
    
    if (languagePairsData.value?.languagePairs) {
      configStore.setLanguagePairs(languagePairsData.value.languagePairs)
    }
  } catch (error: any) {
    console.error('Failed to load language pairs:', error)
    message.error(error.message || t('settings.loadLanguagePairsError'))
  } finally {
    isLoading.value = false
  }
}

// Handle adding a new language pair
async function handleAddLanguagePair() {
  try {
    isAdding.value = true
    
    // Check for duplicate in local store
    const isDuplicate = configStore.languagePairs.some(
      (pair: LanguagePair) =>
        pair.sourceLanguageCode.toLowerCase() === formState.sourceLanguageCode.toLowerCase() &&
        pair.targetLanguageCode.toLowerCase() === formState.targetLanguageCode.toLowerCase()
    )

    if (isDuplicate) {
      message.warning(t('settings.languagePairExists'))
      return
    }

    // Call GraphQL mutation
    const result = await addLanguagePairMutation({
      sourceLanguage: formState.sourceLanguage.trim(),
      targetLanguage: formState.targetLanguage.trim(),
      sourceLanguageCode: formState.sourceLanguageCode.toLowerCase().trim(),
      targetLanguageCode: formState.targetLanguageCode.toLowerCase().trim(),
    })

    if (result?.data?.addLanguagePair) {
      const newPair = result.data.addLanguagePair
      configStore.addLanguagePair(newPair)
      message.success(t('settings.languagePairAdded'))
      
      // Reset form
      formState.sourceLanguage = ''
      formState.targetLanguage = ''
      formState.sourceLanguageCode = ''
      formState.targetLanguageCode = ''
      
      // Reload language pairs to ensure sync
      await loadLanguagePairs()
    }
  } catch (error: any) {
    console.error('Failed to add language pair:', error)
    message.error(error.message || t('settings.languagePairAddError'))
  } finally {
    isAdding.value = false
  }
}

// Handle removing a language pair
async function handleRemoveLanguagePair(id: string) {
  try {
    removingId.value = id
    
    // Call GraphQL mutation
    const result = await removeLanguagePairMutation({ id })

    if (result?.data?.removeLanguagePair) {
      configStore.removeLanguagePair(id)
      message.success(t('settings.languagePairRemoved'))
      
      // Reload language pairs to ensure sync
      await loadLanguagePairs()
    }
  } catch (error: any) {
    console.error('Failed to remove language pair:', error)
    message.error(error.message || t('settings.languagePairRemoveError'))
  } finally {
    removingId.value = null
  }
}

// Load model configuration
async function loadModelConfig() {
  try {
    isLoadingModel.value = true
    await refetchModelConfig()
    
    if (modelConfigData.value?.modelConfig) {
      configStore.setModelConfig(modelConfigData.value.modelConfig)
      selectedModelId.value = modelConfigData.value.modelConfig.modelId
    }
  } catch (error: any) {
    console.error('Failed to load model config:', error)
    message.error(error.message || t('settings.loadModelError'))
  } finally {
    isLoadingModel.value = false
  }
}

// Handle model change
async function handleModelChange(modelId: string) {
  try {
    isUpdatingModel.value = true
    
    // Call GraphQL mutation
    const result = await updateModelMutation({ modelId })

    if (result?.data?.updateModel) {
      const updatedConfig = result.data.updateModel
      configStore.setModelConfig(updatedConfig)
      selectedModelId.value = updatedConfig.modelId
      message.success(t('settings.modelUpdated', { modelName: updatedConfig.modelName }))
    }
  } catch (error: any) {
    console.error('Failed to update model:', error)
    message.error(error.message || t('settings.updateModelError'))
    
    // Revert selection on error
    if (configStore.currentModel.modelId) {
      selectedModelId.value = configStore.currentModel.modelId
    }
  } finally {
    isUpdatingModel.value = false
  }
}

</script>

<style scoped>
.settings-page {
  min-height: calc(100vh - 64px);
  background: transparent;
}

.content {
  padding: 32px 24px;
  max-width: 1400px;
  margin: 0 auto;
  width: 100%;
}

.page-header {
  margin-bottom: 32px;
}

.page-header h1 {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-main);
  margin-bottom: 8px;
}

.subtitle {
  color: var(--text-secondary);
  font-size: 16px;
}

.settings-card {
  margin-bottom: 24px;
}

.card-icon {
  font-size: 20px;
  color: var(--primary-color);
  opacity: 0.7;
}

/* Model Form */
.model-form {
  max-width: 600px;
}

.current-model-info {
  margin-top: 16px;
  background: var(--glass-card-bg);
  padding: 12px 16px;
  border-radius: 8px;
  border: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--text-secondary);
}

.info-icon {
  color: var(--primary-color);
}

/* Inner Sections */
.inner-section {
  padding: 16px 0;
  border-bottom: 1px solid rgba(0,0,0,0.05);
}

.inner-section:last-child {
  border-bottom: none;
}

.inner-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 20px;
  color: var(--text-main);
}

.modern-input {
  border-radius: 8px;
}

.add-button {
  border-radius: 8px;
  height: 48px;
  font-size: 15px;
  font-weight: 600;
}

/* Desktop layout: button aligned with inputs */
.add-button-form-item {
  margin-bottom: 0 !important;
}

/* On desktop, align button with input fields */
@media (min-width: 992px) {
  .add-button-form-item {
    padding-bottom: 24px; /* Match form-item label height */
  }
}

/* Pairs Grid */
.list-section {
  padding-top: 24px;
}

.pairs-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.pair-card {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  transition: all 0.2s;
}

.pair-card:hover {
  border-color: var(--primary-color);
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}

.pair-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.pair-visual {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--glass-card-bg);
  padding: 4px 8px;
  border-radius: 6px;
  width: fit-content;
}

.lang-node {
  font-weight: 700;
  font-size: 12px;
  font-family: monospace;
  color: var(--text-secondary);
}

.pair-arrow {
  font-size: 12px;
  color: var(--primary-color);
}

.pair-names {
  font-size: 14px;
  color: var(--text-main);
  font-weight: 500;
}

.separator {
  color: var(--text-secondary);
  font-weight: 400;
  margin: 0 4px;
  font-size: 12px;
}

.delete-btn {
  color: var(--text-secondary);
}

.delete-btn:hover {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.1);
}


/* Layout */
@media (max-width: 768px) {
  .content {
    padding: 16px;
  }
}
</style>
