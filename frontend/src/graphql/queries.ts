import { gql } from '@apollo/client/core'

// Authentication Queries
export const ME_QUERY = gql`
  query Me {
    me {
      username
      role
      mustChangePassword
    }
  }
`

// Job Queries
export const JOB_QUERY = gql`
  query Job($id: String!) {
    job(id: $id) {
      id
      status
      progress
      filesTotal
      filesCompleted
      filesProcessing {
        filename
        progress
        cellsTotal
        cellsTranslated
      }
      filesFailed {
        filename
        error
      }
      completedFiles {
        originalFilename
        outputFilename
        cellsTranslated
      }
      autoAppend
      createdAt
      completedAt
    }
  }
`

// Language Pair Queries
export const LANGUAGE_PAIRS_QUERY = gql`
  query LanguagePairs {
    languagePairs {
      id
      sourceLanguage
      targetLanguage
      sourceLanguageCode
      targetLanguageCode
    }
  }
`

// Model Configuration Queries
export const MODEL_CONFIG_QUERY = gql`
  query ModelConfig {
    modelConfig {
      modelId
      modelName
      availableModels {
        name
        id
      }
    }
  }
`

// Job History Query (paginated)
export const JOB_HISTORY_QUERY = gql`
  query JobHistory(
    $limit: Int
    $cursor: String
    $status: JobStatus
    $dateFrom: String
    $dateTo: String
  ) {
    jobHistory(
      limit: $limit
      cursor: $cursor
      status: $status
      dateFrom: $dateFrom
      dateTo: $dateTo
    ) {
      jobs {
        id
        status
        progress
        filesTotal
        filesCompleted
        filesProcessing {
          filename
          progress
          segmentsTotal
          segmentsTranslated
          documentType
        }
        filesFailed {
          filename
          error
          errorType
        }
        completedFiles {
          originalFilename
          outputFilename
          segmentsTranslated
          documentType
        }
        languagePair {
          id
          sourceLanguage
          targetLanguage
        }
        autoAppend
        createdAt
        completedAt
      }
      nextCursor
      hasMore
    }
  }
`
