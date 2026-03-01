<template>
  <div ref="containerRef" class="virtual-list" @scroll="handleScroll">
    <div class="virtual-list-spacer" :style="{ height: `${totalHeight}px` }">
      <div class="virtual-list-content" :style="{ transform: `translateY(${offsetY}px)` }">
        <slot
          v-for="item in visibleItems"
          :key="getItemKey(item)"
          :item="item"
          name="item"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts" generic="T">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'

interface Props {
  items: T[]
  itemHeight: number
  bufferSize?: number
  keyField?: keyof T
}

const props = withDefaults(defineProps<Props>(), {
  bufferSize: 5,
  keyField: 'id' as any,
})

const containerRef = ref<HTMLElement | null>(null)
const scrollTop = ref(0)
const containerHeight = ref(0)

// Calculate visible range
const visibleRange = computed(() => {
  const start = Math.floor(scrollTop.value / props.itemHeight)
  const end = Math.ceil((scrollTop.value + containerHeight.value) / props.itemHeight)
  
  return {
    start: Math.max(0, start - props.bufferSize),
    end: Math.min(props.items.length, end + props.bufferSize),
  }
})

// Get visible items
const visibleItems = computed(() => {
  const { start, end } = visibleRange.value
  return props.items.slice(start, end)
})

// Calculate total height
const totalHeight = computed(() => {
  return props.items.length * props.itemHeight
})

// Calculate offset
const offsetY = computed(() => {
  return visibleRange.value.start * props.itemHeight
})

// Get item key
function getItemKey(item: T): string | number {
  if (typeof item === 'object' && item !== null && props.keyField in item) {
    return String(item[props.keyField])
  }
  return String(item)
}

// Handle scroll
function handleScroll() {
  if (containerRef.value) {
    scrollTop.value = containerRef.value.scrollTop
  }
}

// Update container height
function updateContainerHeight() {
  if (containerRef.value) {
    containerHeight.value = containerRef.value.clientHeight
  }
}

// Resize observer
let resizeObserver: ResizeObserver | null = null

onMounted(() => {
  updateContainerHeight()
  
  if (containerRef.value) {
    resizeObserver = new ResizeObserver(updateContainerHeight)
    resizeObserver.observe(containerRef.value)
  }
})

onUnmounted(() => {
  if (resizeObserver && containerRef.value) {
    resizeObserver.unobserve(containerRef.value)
    resizeObserver.disconnect()
  }
})

// Watch for items changes
watch(() => props.items.length, () => {
  // Reset scroll position if items change significantly
  if (scrollTop.value > totalHeight.value) {
    scrollTop.value = 0
    if (containerRef.value) {
      containerRef.value.scrollTop = 0
    }
  }
})
</script>

<style scoped>
.virtual-list {
  overflow-y: auto;
  overflow-x: hidden;
  height: 100%;
  width: 100%;
  position: relative;
}

.virtual-list-spacer {
  position: relative;
  width: 100%;
}

.virtual-list-content {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  will-change: transform;
}
</style>
