import { ref, computed, watchEffect } from 'vue'

export type ThemeMode = 'light' | 'dark' | 'system'

const STORAGE_KEY = 'ui_theme'

function getInitialMode(): ThemeMode {
  if (typeof window === 'undefined') return 'system'
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored === 'light' || stored === 'dark' || stored === 'system') return stored
  return 'system'
}

const mode = ref<ThemeMode>(getInitialMode())
const isDark = ref(false)

function applyMode(value: ThemeMode) {
  const prefersDark =
    typeof window !== 'undefined' && window.matchMedia('(prefers-color-scheme: dark)').matches
  isDark.value = value === 'dark' || (value === 'system' && prefersDark)

  const root = document.documentElement
  root.classList.toggle('dark', isDark.value)
  root.style.colorScheme = isDark.value ? 'dark' : 'light'
}

if (typeof window !== 'undefined') {
  watchEffect(() => {
    applyMode(mode.value)
    localStorage.setItem(STORAGE_KEY, mode.value)
  })

  // 跟随系统主题变化（system 模式下实时响应）
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
    if (mode.value === 'system') applyMode('system')
  })
}

export function useTheme() {
  const cycleOrder: ThemeMode[] = ['light', 'dark', 'system']

  function setTheme(value: ThemeMode) {
    mode.value = value
  }

  function toggleTheme() {
    mode.value = isDark.value ? 'light' : 'dark'
  }

  function cycleTheme() {
    const index = cycleOrder.indexOf(mode.value)
    mode.value = cycleOrder[(index + 1) % cycleOrder.length] ?? 'system'
  }

  return {
    mode: computed(() => mode.value),
    isDark: computed(() => isDark.value),
    setTheme,
    toggleTheme,
    cycleTheme,
  }
}
