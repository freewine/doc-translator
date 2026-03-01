import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'

/**
 * Composable for permission checks
 */
export function usePermission() {
  const authStore = useAuthStore()

  /**
   * Check if current user is admin
   */
  const isAdmin = computed(() => authStore.isAdmin)

  /**
   * Check if current user can delete a specific user
   */
  function canDeleteUser(username: string): boolean {
    // Cannot delete self
    if (authStore.user?.username === username) {
      return false
    }
    return authStore.isAdmin
  }

  /**
   * Check if current user can edit a specific user's role
   */
  function canEditUserRole(username: string): boolean {
    // Cannot edit own role
    if (authStore.user?.username === username) {
      return false
    }
    return authStore.isAdmin
  }

  return {
    isAdmin,
    canDeleteUser,
    canEditUserRole,
  }
}
