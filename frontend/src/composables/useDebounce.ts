import { ref, watch, type Ref } from 'vue'

/**
 * Debounce a reactive value with a specified delay.
 * Returns a new ref that updates only after the delay has passed
 * without changes to the source value.
 */
export function useDebounce<T>(value: Ref<T>, delay = 300): Ref<T> {
  const debouncedValue = ref(value.value) as Ref<T>
  let timeoutId: ReturnType<typeof setTimeout> | null = null

  watch(value, (newValue) => {
    if (timeoutId !== null) {
      clearTimeout(timeoutId)
    }
    timeoutId = setTimeout(() => {
      debouncedValue.value = newValue
    }, delay)
  })

  return debouncedValue
}
