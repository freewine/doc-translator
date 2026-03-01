import { gql } from '@apollo/client/core'

// Authentication Mutations
export const LOGIN_MUTATION = gql`
  mutation Login($username: String!, $password: String!) {
    login(username: $username, password: $password) {
      token
      user {
        username
        role
        mustChangePassword
      }
    }
  }
`

export const LOGOUT_MUTATION = gql`
  mutation Logout {
    logout
  }
`

// Job Mutations
export const CREATE_TRANSLATION_JOB_MUTATION = gql`
  mutation CreateTranslationJob(
    $fileIds: [String!]!, 
    $languagePairId: String!, 
    $catalogIds: [String!],
    $autoAppend: Boolean,
    $interleavedMode: Boolean
  ) {
    createTranslationJob(
      fileIds: $fileIds, 
      languagePairId: $languagePairId, 
      catalogIds: $catalogIds,
      autoAppend: $autoAppend,
      interleavedMode: $interleavedMode
    ) {
      id
      status
      progress
      filesTotal
      filesCompleted
      autoAppend
      interleavedMode
      createdAt
    }
  }
`

// Language Pair Mutations
export const ADD_LANGUAGE_PAIR_MUTATION = gql`
  mutation AddLanguagePair(
    $sourceLanguage: String!
    $targetLanguage: String!
    $sourceLanguageCode: String!
    $targetLanguageCode: String!
  ) {
    addLanguagePair(
      sourceLanguage: $sourceLanguage
      targetLanguage: $targetLanguage
      sourceLanguageCode: $sourceLanguageCode
      targetLanguageCode: $targetLanguageCode
    ) {
      id
      sourceLanguage
      targetLanguage
      sourceLanguageCode
      targetLanguageCode
    }
  }
`

export const REMOVE_LANGUAGE_PAIR_MUTATION = gql`
  mutation RemoveLanguagePair($id: String!) {
    removeLanguagePair(id: $id)
  }
`

// Model Configuration Mutations
export const UPDATE_MODEL_MUTATION = gql`
  mutation UpdateModel($modelId: String!) {
    updateModel(modelId: $modelId) {
      modelId
      modelName
      availableModels {
        name
        id
      }
    }
  }
`
