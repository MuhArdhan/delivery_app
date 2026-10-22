import { onMounted, onBeforeUnmount } from 'vue'

// Only refresh mounted views while the browser tab is visible.
export function useVisibleRefresh(refresh, interval = 30000) {
  let timer
  let running = false
  async function tick() {
    if (document.hidden || running) return
    running = true
    try {
      await refresh()
    } finally {
      running = false
    }
  }
  onMounted(() => {
    timer = window.setInterval(tick, interval)
    document.addEventListener('visibilitychange', tick)
  })
  onBeforeUnmount(() => {
    window.clearInterval(timer)
    document.removeEventListener('visibilitychange', tick)
  })
}
