import { ref, type Ref } from 'vue'
import { apolloClient } from '../services/apollo'
import { gql, type DocumentNode, type OperationVariables } from '@apollo/client/core'

/**
 * Composable for executing GraphQL queries.
 * Call execute() or refetch() to run the query.
 */
export function useQuery<TData = any, TVariables extends OperationVariables = OperationVariables>(
  query: DocumentNode,
  defaultVariables?: TVariables
) {
  const data: Ref<TData | null> = ref(null)
  const loading = ref(false)
  const error: Ref<Error | null> = ref(null)

  async function execute(variables?: TVariables) {
    loading.value = true
    error.value = null

    try {
      const result = await apolloClient.query<TData, TVariables>({
        query,
        variables: (variables ?? defaultVariables) as TVariables,
      })
      data.value = result.data ?? null
      return result
    } catch (e) {
      error.value = e as Error
      throw e
    } finally {
      loading.value = false
    }
  }

  return {
    data,
    loading,
    error,
    execute,
    refetch: execute, // Alias for semantic clarity when re-running a query
  }
}

/**
 * Composable for executing GraphQL mutations.
 */
export function useMutation<TData = any, TVariables extends OperationVariables = OperationVariables>(
  mutation: DocumentNode
) {
  const data: Ref<TData | null> = ref(null)
  const loading = ref(false)
  const error: Ref<Error | null> = ref(null)

  async function mutate(variables?: TVariables) {
    loading.value = true
    error.value = null

    try {
      const result = await apolloClient.mutate<TData, TVariables>({
        mutation,
        variables: variables as TVariables,
      })
      data.value = result.data ?? null
      return result
    } catch (e) {
      error.value = e as Error
      throw e
    } finally {
      loading.value = false
    }
  }

  function reset() {
    data.value = null
    error.value = null
    loading.value = false
  }

  return {
    data,
    loading,
    error,
    mutate,
    reset,
  }
}

/**
 * Composable for lazy queries (queries that don't execute immediately).
 * Includes a 'called' flag to track if the query has been executed.
 */
export function useLazyQuery<TData = any, TVariables extends OperationVariables = OperationVariables>(
  query: DocumentNode
) {
  const data: Ref<TData | null> = ref(null)
  const loading = ref(false)
  const error: Ref<Error | null> = ref(null)
  const called = ref(false)

  async function execute(variables?: TVariables) {
    loading.value = true
    error.value = null
    called.value = true

    try {
      const result = await apolloClient.query<TData, TVariables>({
        query,
        variables: variables as TVariables,
      })
      data.value = result.data ?? null
      return result
    } catch (e) {
      error.value = e as Error
      throw e
    } finally {
      loading.value = false
    }
  }

  return {
    data,
    loading,
    error,
    called,
    execute,
  }
}

// Re-export gql for convenience
export { gql }
