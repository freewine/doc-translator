import { ref, type Ref } from 'vue'
import { notification } from 'ant-design-vue'
import type { NotificationPlacement } from 'ant-design-vue/es/notification/interface'

export interface ErrorHandlerOptions {
  showNotification?: boolean
  retryable?: boolean
  maxRetries?: number
  retryDelay?: number
  placement?: NotificationPlacement
}

export interface ErrorState {
  message: string
  code?: string
  details?: unknown
  timestamp: Date
  retryCount: number
}

/**
 * Composable for handling errors with user feedback and optional retry functionality.
 */
export function useErrorHandler(options: ErrorHandlerOptions = {}) {
  const {
    showNotification = true,
    retryable = false,
    maxRetries = 3,
    retryDelay = 1000,
    placement = 'topRight',
  } = options

  const error: Ref<ErrorState | null> = ref(null)
  const isRetrying = ref(false)
  const retryCount = ref(0)

  /**
   * Handle an error with user-friendly messaging.
   */
  function handleError(err: unknown, context?: string) {
    const errorMessage = extractErrorMessage(err)
    const errorCode = extractErrorCode(err)

    error.value = {
      message: errorMessage,
      code: errorCode,
      details: err,
      timestamp: new Date(),
      retryCount: retryCount.value,
    }

    if (showNotification) {
      const description = context
        ? `${context}: ${errorMessage}${errorCode ? ` (${errorCode})` : ''}`
        : errorMessage

      notification.error({
        message: 'Error',
        description,
        placement,
        duration: 5,
      })
    }

    console.error(`Error${context ? ` in ${context}` : ''}:`, err)
  }

  /**
   * Handle an error with automatic retry using exponential backoff.
   */
  async function handleErrorWithRetry(
    err: unknown,
    retryFn: () => Promise<unknown>,
    context?: string
  ): Promise<boolean> {
    handleError(err, context)

    if (!retryable || retryCount.value >= maxRetries) {
      return false
    }

    isRetrying.value = true
    retryCount.value++

    try {
      // Exponential backoff delay
      const delay = retryDelay * Math.pow(2, retryCount.value - 1)
      await new Promise(resolve => setTimeout(resolve, delay))

      await retryFn()

      // Success - reset state
      retryCount.value = 0
      clearError()

      if (showNotification) {
        notification.success({
          message: 'Success',
          description: 'Operation completed successfully after retry',
          placement,
        })
      }

      return true
    } catch (retryErr) {
      return handleErrorWithRetry(retryErr, retryFn, context)
    } finally {
      isRetrying.value = false
    }
  }

  /**
   * Clear the current error state.
   */
  function clearError() {
    error.value = null
    retryCount.value = 0
  }

  /**
   * Show a success notification.
   */
  function showSuccess(message: string, description?: string) {
    notification.success({ message, description, placement, duration: 3 })
  }

  /**
   * Show a warning notification.
   */
  function showWarning(message: string, description?: string) {
    notification.warning({ message, description, placement, duration: 4 })
  }

  return {
    error,
    isRetrying,
    retryCount,
    handleError,
    handleErrorWithRetry,
    clearError,
    showSuccess,
    showWarning,
  }
}

// Type guard for objects with properties
function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

/**
 * Extract user-friendly error message from various error types.
 */
function extractErrorMessage(err: unknown): string {
  if (typeof err === 'string') {
    return err
  }

  if (!isObject(err)) {
    return 'An unexpected error occurred'
  }

  // GraphQL errors from Apollo
  if (Array.isArray(err.graphQLErrors) && err.graphQLErrors.length > 0) {
    const firstError = err.graphQLErrors[0]
    if (isObject(firstError) && typeof firstError.message === 'string') {
      return firstError.message
    }
  }

  // Network errors with status codes
  if (isObject(err.networkError)) {
    const statusCode = err.networkError.statusCode
    if (typeof statusCode === 'number') {
      if (statusCode === 401) return 'Authentication failed. Please log in again.'
      if (statusCode === 403) return 'You do not have permission to perform this action.'
      if (statusCode === 404) return 'The requested resource was not found.'
      if (statusCode >= 500) return 'Server error. Please try again later.'
    }
    if (typeof err.networkError.message === 'string') {
      return err.networkError.message
    }
    return 'Network error occurred'
  }

  // Standard Error objects
  if (typeof err.message === 'string') {
    return err.message
  }

  // Nested error property
  if (err.error !== undefined) {
    return extractErrorMessage(err.error)
  }

  return 'An unexpected error occurred'
}

/**
 * Extract error code from error object.
 */
function extractErrorCode(err: unknown): string | undefined {
  if (!isObject(err)) {
    return undefined
  }

  if (typeof err.code === 'string') {
    return err.code
  }

  if (isObject(err.networkError) && typeof err.networkError.statusCode === 'number') {
    return `HTTP_${err.networkError.statusCode}`
  }

  if (Array.isArray(err.graphQLErrors) && err.graphQLErrors.length > 0) {
    const firstError = err.graphQLErrors[0]
    if (isObject(firstError) && isObject(firstError.extensions)) {
      const code = firstError.extensions.code
      if (typeof code === 'string') {
        return code
      }
    }
  }

  return undefined
}

/**
 * Check if an error is transient and can be retried.
 */
export function isTransientError(err: unknown): boolean {
  const message = extractErrorMessage(err).toLowerCase()
  const code = extractErrorCode(err)

  // Server errors (5xx)
  if (code?.startsWith('HTTP_5')) {
    return true
  }

  // Timeout errors
  if (message.includes('timeout') || message.includes('timed out')) {
    return true
  }

  // Connection errors
  if (
    message.includes('network') ||
    message.includes('connection') ||
    message.includes('econnrefused') ||
    message.includes('enotfound')
  ) {
    return true
  }

  // Rate limiting
  if (code === 'HTTP_429' || message.includes('rate limit')) {
    return true
  }

  return false
}
