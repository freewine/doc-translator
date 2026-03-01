import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { apolloClient } from '@/services/apollo'
import { LOGIN_MUTATION, LOGOUT_MUTATION } from '@/graphql/mutations'
import { ME_QUERY } from '@/graphql/queries'
import { CHANGE_PASSWORD_MUTATION } from '@/graphql/user'
import type { User, AuthPayload, ChangePasswordInput, UserRole } from '@/types'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const token = ref<string | null>(null)
  const isAuthenticated = computed(() => !!token.value)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  // Role-based computed properties
  const isAdmin = computed(() => user.value?.role === 'admin')
  const mustChangePassword = computed(() => user.value?.mustChangePassword ?? false)

  // Token refresh interval (23 hours for 24-hour token)
  let refreshInterval: number | null = null

  /**
   * Login with username and password
   */
  async function login(username: string, password: string): Promise<{ success: boolean; mustChangePassword: boolean }> {
    isLoading.value = true
    error.value = null

    try {
      const result = await apolloClient.mutate<{ login: AuthPayload }>({
        mutation: LOGIN_MUTATION,
        variables: { username, password },
      })

      if (result.data?.login) {
        const { token: newToken, user: newUser } = result.data.login
        setAuth(newToken, newUser)
        startTokenRefresh()
        return { 
          success: true, 
          mustChangePassword: newUser.mustChangePassword ?? false 
        }
      } else if (result.error) {
        error.value = result.error.message || 'Login failed'
        return { success: false, mustChangePassword: false }
      }

      error.value = 'Login failed: No data returned'
      return { success: false, mustChangePassword: false }
    } catch (err: any) {
      error.value = err.message || 'Login failed'
      console.error('Login error:', err)
      return { success: false, mustChangePassword: false }
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Logout and clear authentication
   */
  async function logout(): Promise<void> {
    isLoading.value = true
    error.value = null

    try {
      await apolloClient.mutate({
        mutation: LOGOUT_MUTATION,
      })
    } catch (err: any) {
      console.error('Logout error:', err)
      // Continue with local logout even if server logout fails
    } finally {
      clearAuth()
      stopTokenRefresh()
      isLoading.value = false
    }
  }

  /**
   * Fetch current user information
   */
  async function fetchUser(): Promise<boolean> {
    if (!token.value) {
      return false
    }

    isLoading.value = true
    error.value = null

    try {
      const result = await apolloClient.query<{ me: User }>({
        query: ME_QUERY,
        fetchPolicy: 'network-only',
      })

      if (result.data?.me) {
        user.value = result.data.me
        return true
      } else if (result.error) {
        error.value = result.error.message || 'Failed to fetch user'
        clearAuth()
        return false
      }

      error.value = 'Failed to fetch user: No data returned'
      clearAuth()
      return false
    } catch (err: any) {
      error.value = err.message || 'Failed to fetch user'
      console.error('Fetch user error:', err)
      clearAuth()
      return false
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Set authentication state
   */
  function setAuth(newToken: string, newUser: User) {
    token.value = newToken
    user.value = newUser
    localStorage.setItem('auth_token', newToken)
    localStorage.setItem('auth_token_timestamp', Date.now().toString())
  }

  /**
   * Clear authentication state
   */
  function clearAuth() {
    token.value = null
    user.value = null
    localStorage.removeItem('auth_token')
    localStorage.removeItem('auth_token_timestamp')
    apolloClient.clearStore()
  }

  /**
   * Load authentication from localStorage
   */
  async function loadAuth(): Promise<boolean> {
    const savedToken = localStorage.getItem('auth_token')
    const timestamp = localStorage.getItem('auth_token_timestamp')

    if (!savedToken) {
      return false
    }

    // Check if token is expired (24 hours)
    if (timestamp) {
      const tokenAge = Date.now() - parseInt(timestamp, 10)
      const maxAge = 24 * 60 * 60 * 1000 // 24 hours in milliseconds

      if (tokenAge > maxAge) {
        clearAuth()
        return false
      }
    }

    token.value = savedToken

    // Fetch user info to verify token is still valid
    const success = await fetchUser()

    if (success) {
      startTokenRefresh()
    }

    return success
  }

  /**
   * Start automatic token refresh
   * Refreshes token every 23 hours (before 24-hour expiration)
   */
  function startTokenRefresh() {
    stopTokenRefresh()

    // Refresh every 23 hours
    const refreshIntervalMs = 23 * 60 * 60 * 1000

    refreshInterval = window.setInterval(async () => {
      if (token.value && user.value) {
        // Re-login to get a fresh token
        // In a production app, you'd have a dedicated refresh token endpoint
        console.log('Token refresh would happen here')
        // For now, we'll just update the timestamp
        localStorage.setItem('auth_token_timestamp', Date.now().toString())
      }
    }, refreshIntervalMs)
  }

  /**
   * Stop automatic token refresh
   */
  function stopTokenRefresh() {
    if (refreshInterval !== null) {
      clearInterval(refreshInterval)
      refreshInterval = null
    }
  }

  /**
   * Clear error message
   */
  function clearError() {
    error.value = null
  }

  /**
   * Change password
   */
  async function changePassword(input: ChangePasswordInput): Promise<boolean> {
    isLoading.value = true
    error.value = null

    try {
      const result = await apolloClient.mutate<{ changeMyPassword: boolean }>({
        mutation: CHANGE_PASSWORD_MUTATION,
        variables: {
          currentPassword: input.currentPassword,
          newPassword: input.newPassword,
        },
      })

      // Check for GraphQL errors
      if (result.error) {
        const errorMessage = result.error.message || 'Failed to change password'
        error.value = errorMessage
        console.error('Change password GraphQL error:', result.error)
        throw new Error(errorMessage)
      }

      if (result.data?.changeMyPassword === true) {
        // Update user state to reflect password change
        if (user.value) {
          user.value = { ...user.value, mustChangePassword: false }
        }
        console.log('Password changed successfully, mustChangePassword set to false')
        return true
      }

      // Unexpected response - throw error
      const unexpectedError = 'Unexpected response from server'
      error.value = unexpectedError
      console.error('Change password unexpected response:', result)
      throw new Error(unexpectedError)
    } catch (err: any) {
      error.value = err.message || 'Failed to change password'
      console.error('Change password error:', err)
      throw err
    } finally {
      isLoading.value = false
    }
  }

  return {
    // State
    user,
    token,
    isAuthenticated,
    isLoading,
    error,

    // Role-based computed
    isAdmin,
    mustChangePassword,

    // Actions
    login,
    logout,
    fetchUser,
    loadAuth,
    clearError,
    setAuth,
    clearAuth,
    changePassword,
  }
})
