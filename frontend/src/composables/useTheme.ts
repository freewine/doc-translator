import { ref, watch, onMounted, computed } from 'vue'

export type Theme = 'light' | 'dark'

const THEME_KEY = 'app_theme'

// Global state shared across all composable instances
const currentTheme = ref<Theme>('light')

export function useTheme() {
    function applyTheme(theme: Theme) {
        if (theme === 'dark') {
            document.documentElement.setAttribute('data-theme', 'dark')
            document.documentElement.style.colorScheme = 'dark'
        } else {
            document.documentElement.removeAttribute('data-theme')
            document.documentElement.style.colorScheme = 'light'
        }
    }

    function toggleTheme() {
        currentTheme.value = currentTheme.value === 'light' ? 'dark' : 'light'
    }

    function initTheme() {
        const savedTheme = localStorage.getItem(THEME_KEY) as Theme | null
        if (savedTheme === 'light' || savedTheme === 'dark') {
            currentTheme.value = savedTheme
        } else {
            // Use system preference as default
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
            currentTheme.value = prefersDark ? 'dark' : 'light'
        }
        applyTheme(currentTheme.value)
    }

    // Persist and apply changes
    watch(currentTheme, (newTheme) => {
        localStorage.setItem(THEME_KEY, newTheme)
        applyTheme(newTheme)
    })

    // Listen for system preference changes when no manual override exists
    onMounted(() => {
        const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
        const handleChange = (e: MediaQueryListEvent) => {
            if (!localStorage.getItem(THEME_KEY)) {
                currentTheme.value = e.matches ? 'dark' : 'light'
            }
        }
        mediaQuery.addEventListener('change', handleChange)
    })

    return {
        theme: currentTheme,
        toggleTheme,
        initTheme,
        isDark: computed(() => currentTheme.value === 'dark')
    }
}
