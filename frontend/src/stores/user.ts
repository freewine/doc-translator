import { defineStore } from 'pinia'
import { ref } from 'vue'
import { apolloClient } from '@/services/apollo'
import { USERS_QUERY, CREATE_USER_MUTATION, UPDATE_USER_MUTATION, DELETE_USER_MUTATION, UNLOCK_USER_MUTATION } from '@/graphql/user'
import type { User, CreateUserInput, UpdateUserInput } from '@/types'

export const useUserStore = defineStore('user', () => {
  const users = ref<User[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  /**
   * Fetch users list
   */
  async function fetchUsers(includeDeleted = false): Promise<void> {
    isLoading.value = true
    error.value = null

    try {
      const result = await apolloClient.query<{ users: User[] }>({
        query: USERS_QUERY,
        variables: { includeDeleted },
        fetchPolicy: 'network-only',
      })

      if (result.data?.users) {
        users.value = result.data.users
      }
    } catch (err: any) {
      error.value = err.message || 'Failed to fetch users'
      console.error('Fetch users error:', err)
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Create a new user
   */
  async function createUser(input: CreateUserInput): Promise<User | null> {
    isLoading.value = true
    error.value = null

    try {
      const result = await apolloClient.mutate<{ createUser: User }>({
        mutation: CREATE_USER_MUTATION,
        variables: {
          username: input.username,
          password: input.password,
          role: input.role,
        },
      })

      if (result.data?.createUser) {
        // Refresh user list
        await fetchUsers()
        return result.data.createUser
      }
      return null
    } catch (err: any) {
      error.value = err.message || 'Failed to create user'
      console.error('Create user error:', err)
      throw err
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Update an existing user
   */
  async function updateUser(username: string, input: UpdateUserInput): Promise<User | null> {
    isLoading.value = true
    error.value = null

    try {
      const result = await apolloClient.mutate<{ updateUser: User }>({
        mutation: UPDATE_USER_MUTATION,
        variables: {
          username,
          password: input.password || null,
          role: input.role || null,
        },
      })

      if (result.data?.updateUser) {
        // Refresh user list
        await fetchUsers()
        return result.data.updateUser
      }
      return null
    } catch (err: any) {
      error.value = err.message || 'Failed to update user'
      console.error('Update user error:', err)
      throw err
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Delete a user
   */
  async function deleteUser(username: string): Promise<boolean> {
    isLoading.value = true
    error.value = null

    try {
      const result = await apolloClient.mutate<{ deleteUser: boolean }>({
        mutation: DELETE_USER_MUTATION,
        variables: { username },
      })

      if (result.data?.deleteUser) {
        // Refresh user list
        await fetchUsers()
        return true
      }
      return false
    } catch (err: any) {
      error.value = err.message || 'Failed to delete user'
      console.error('Delete user error:', err)
      throw err
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Unlock a locked user
   */
  async function unlockUser(username: string): Promise<User | null> {
    isLoading.value = true
    error.value = null

    try {
      const result = await apolloClient.mutate<{ unlockUser: User }>({
        mutation: UNLOCK_USER_MUTATION,
        variables: { username },
      })

      if (result.data?.unlockUser) {
        // Refresh user list
        await fetchUsers()
        return result.data.unlockUser
      }
      return null
    } catch (err: any) {
      error.value = err.message || 'Failed to unlock user'
      console.error('Unlock user error:', err)
      throw err
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Clear error message
   */
  function clearError() {
    error.value = null
  }

  return {
    // State
    users,
    isLoading,
    error,

    // Actions
    fetchUsers,
    createUser,
    updateUser,
    deleteUser,
    unlockUser,
    clearError,
  }
})
