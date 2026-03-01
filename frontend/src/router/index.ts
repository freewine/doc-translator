import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Home',
    redirect: '/login',
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginPage.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/main',
    name: 'Main',
    component: () => import('@/views/MainPage.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('@/views/SettingsPage.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/thesaurus',
    name: 'Thesaurus',
    component: () => import('@/views/ThesaurusView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/users',
    name: 'UserManagement',
    component: () => import('@/views/UserManagement.vue'),
    meta: { requiresAuth: true, requiresAdmin: true },
  },
  {
    path: '/change-password',
    name: 'ChangePassword',
    component: () => import('@/views/ChangePasswordPage.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFoundPage.vue'),
    meta: { requiresAuth: false },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// Navigation guard for authentication
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()

  // Load auth from localStorage if not already loaded
  if (!authStore.isAuthenticated && !authStore.isLoading) {
    const token = localStorage.getItem('auth_token')
    if (token) {
      // Try to restore session
      await authStore.loadAuth()
    }
  }

  const requiresAuth = to.meta.requiresAuth === true
  const requiresAdmin = to.meta.requiresAdmin === true

  if (requiresAuth && !authStore.isAuthenticated) {
    // Redirect to login if authentication is required but user is not authenticated
    next({
      path: '/login',
      query: { redirect: to.fullPath }, // Save the intended destination
    })
  } else if (requiresAdmin && !authStore.isAdmin) {
    // Redirect to main page if admin is required but user is not admin
    next('/main')
  } else if (to.path === '/login' && authStore.isAuthenticated) {
    // Redirect to main page if already authenticated and trying to access login
    // But check if password change is required first
    if (authStore.mustChangePassword) {
      next('/change-password')
    } else {
      const redirect = (to.query.redirect as string) || '/main'
      next(redirect)
    }
  } else if (authStore.isAuthenticated && authStore.mustChangePassword && to.path !== '/change-password') {
    // Force password change if required
    next('/change-password')
  } else {
    // Allow navigation
    next()
  }
})

export default router
