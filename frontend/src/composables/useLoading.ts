import { ref, computed, reactive } from 'vue'

/**
 * Composable for managing multiple named loading states.
 * Use when you need to track loading for different operations independently.
 */
export function useLoading(initialKeys: string[] = []) {
  // Use reactive for the loading states map
  const loadingStates = reactive<Record<string, boolean>>(
    Object.fromEntries(initialKeys.map(key => [key, false]))
  )

  // Computed property that's true when any key is loading
  const isLoading = computed(() => Object.values(loadingStates).some(Boolean))

  /**
   * Check if a specific key is loading
   */
  function isKeyLoading(key: string): boolean {
    return loadingStates[key] ?? false
  }

  /**
   * Execute an async function with automatic loading state management
   */
  async function withLoading<T>(fn: () => Promise<T>, key?: string): Promise<T> {
    if (key) {
      loadingStates[key] = true
    }
    try {
      return await fn()
    } finally {
      if (key) {
        loadingStates[key] = false
      }
    }
  }

  /**
   * Reset all loading states to false
   */
  function resetLoading() {
    for (const key of Object.keys(loadingStates)) {
      loadingStates[key] = false
    }
  }

  return {
    loading: loadingStates,
    isLoading,
    isKeyLoading,
    withLoading,
    resetLoading,
  }
}
