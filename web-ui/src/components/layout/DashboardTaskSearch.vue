<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { LoaderCircle, Search, Sparkles } from 'lucide-vue-next'
import Badge from '@/components/ui/badge/Badge.vue'
import * as taskApi from '@/api/tasks'
import { useWebSocket } from '@/composables/useWebSocket'
import type { Task } from '@/types/task.d.ts'

const MAX_RESULTS = 6

const router = useRouter()
const { t } = useI18n()
const { on } = useWebSocket()
const rootRef = ref<HTMLElement | null>(null)
const query = ref('')
const tasks = ref<Task[]>([])
const isLoading = ref(false)
const error = ref('')
const isOpen = ref(false)
const highlightedIndex = ref(0)

const normalizedQuery = computed(() => query.value.trim().toLowerCase())

const visibleTasks = computed(() => {
  const list = normalizedQuery.value
    ? tasks.value.filter((task) => matchesTask(task, normalizedQuery.value))
    : tasks.value
  return list.slice(0, MAX_RESULTS)
})

const panelTitle = computed(() => (
  normalizedQuery.value ? t('tasks.search.matchingTasks') : t('tasks.search.recentTasks')
))

const shouldShowPanel = computed(() => (
  isOpen.value && (
    isLoading.value ||
    Boolean(error.value) ||
    visibleTasks.value.length > 0 ||
    Boolean(normalizedQuery.value)
  )
))

function matchesTask(task: Task, value: string) {
  const fields = [
    task.task_name,
    task.keyword,
    task.description || '',
    task.region || '',
  ]
  return fields.some((field) => field.toLowerCase().includes(value))
}

function getTaskStatus(task: Task) {
  if (task.is_running) return t('common.running')
  if (task.enabled) return t('common.enabled')
  return t('common.disabled')
}

function getTaskMeta(task: Task) {
  const parts = [task.keyword]
  if (task.region) parts.push(task.region)
  parts.push(t('tasks.search.maxPages', { count: task.max_pages }))
  return parts.join(' · ')
}

async function fetchTasks() {
  isLoading.value = true
  error.value = ''
  try {
    tasks.value = await taskApi.getAllTasks()
  } catch (e) {
    error.value = e instanceof Error ? e.message : t('tasks.search.loadFailed')
  } finally {
    isLoading.value = false
  }
}

function ensureLoaded() {
  if (tasks.value.length || isLoading.value) return
  fetchTasks()
}

function openPanel() {
  ensureLoaded()
  isOpen.value = true
}

function closePanel() {
  isOpen.value = false
  highlightedIndex.value = 0
}

function selectTask(task: Task) {
  closePanel()
  router.push({
    name: 'Tasks',
    query: { edit: String(task.id) },
  })
}

function moveHighlight(direction: 1 | -1) {
  if (!visibleTasks.value.length) return
  const lastIndex = visibleTasks.value.length - 1
  const nextIndex = highlightedIndex.value + direction
  if (nextIndex < 0) {
    highlightedIndex.value = lastIndex
    return
  }
  if (nextIndex > lastIndex) {
    highlightedIndex.value = 0
    return
  }
  highlightedIndex.value = nextIndex
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    closePanel()
    return
  }
  if (event.key === 'ArrowDown') {
    event.preventDefault()
    openPanel()
    moveHighlight(1)
    return
  }
  if (event.key === 'ArrowUp') {
    event.preventDefault()
    openPanel()
    moveHighlight(-1)
    return
  }
  if (event.key === 'Enter' && visibleTasks.value.length) {
    event.preventDefault()
    const selectedTask = visibleTasks.value[highlightedIndex.value]
    if (selectedTask) {
      selectTask(selectedTask)
    }
  }
}

function handlePointerDown(event: MouseEvent) {
  if (!rootRef.value) return
  const target = event.target
  if (target instanceof Node && !rootRef.value.contains(target)) {
    closePanel()
  }
}

watch(normalizedQuery, () => {
  highlightedIndex.value = 0
  if (!query.value.trim()) return
  openPanel()
})

on('tasks_updated', fetchTasks)
on('task_status_changed', fetchTasks)

onMounted(() => {
  document.addEventListener('mousedown', handlePointerDown)
})

onBeforeUnmount(() => {
  document.removeEventListener('mousedown', handlePointerDown)
})
</script>
<template>
  <div ref="rootRef" class="relative w-full">
    <Search class="absolute left-3 top-1/2 z-10 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
    <input
      v-model="query"
      type="text"
      :placeholder="t('tasks.search.placeholder')"
      class="h-9 w-full rounded-md border border-input bg-transparent pl-9 pr-14 text-sm outline-none transition-colors placeholder:text-muted-foreground focus-visible:ring-2 focus-visible:ring-ring/30"
      @focus="openPanel"
      @keydown="handleKeydown"
    />
    <kbd class="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 rounded border bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
      ESC
    </kbd>

    <transition name="search-panel">
      <div
        v-if="shouldShowPanel"
        class="absolute inset-x-0 top-[calc(100%+0.5rem)] z-50 overflow-hidden rounded-lg border bg-popover text-popover-foreground shadow-lg"
      >
        <div class="flex items-center justify-between border-b px-4 py-3">
          <div>
            <p class="text-xs font-medium text-muted-foreground">{{ panelTitle }}</p>
            <p class="mt-1 text-xs text-muted-foreground/80">
              {{ normalizedQuery ? t('tasks.search.resultCount', { count: visibleTasks.length }) : t('tasks.search.enterHint') }}
            </p>
          </div>
          <Badge variant="secondary" class="text-[10px] text-muted-foreground">
            {{ t('routes.tasks') }}
          </Badge>
        </div>

        <div v-if="isLoading" class="flex items-center gap-2 px-4 py-6 text-sm text-muted-foreground">
          <LoaderCircle class="h-4 w-4 animate-spin" />
          {{ t('tasks.search.loading') }}
        </div>

        <div v-else-if="error" class="px-4 py-6 text-sm text-destructive">
          {{ error }}
        </div>

        <div v-else-if="visibleTasks.length === 0" class="px-4 py-6">
          <p class="text-sm font-medium">{{ t('tasks.search.emptyTitle') }}</p>
          <p class="mt-1 text-xs text-muted-foreground">{{ t('tasks.search.emptyDescription') }}</p>
        </div>

        <div v-else class="divide-y divide-border/60">
          <button
            v-for="(task, index) in visibleTasks"
            :key="task.id"
            class="flex w-full items-start gap-3 px-4 py-3 text-left transition-colors"
            :class="index === highlightedIndex ? 'bg-accent text-accent-foreground' : 'hover:bg-accent/50'"
            @mouseenter="highlightedIndex = index"
            @click="selectTask(task)"
          >
            <div
              class="mt-1.5 h-2 w-2 shrink-0 rounded-full"
              :class="task.is_running ? 'bg-success' : task.enabled ? 'bg-primary' : 'bg-muted-foreground/40'"
            />

            <div class="min-w-0 flex-1">
              <div class="flex items-center justify-between gap-3">
                <p class="truncate text-sm font-medium">{{ task.task_name }}</p>
                <Badge
                  variant="outline"
                  class="shrink-0 text-[10px] text-muted-foreground"
                >
                  {{ getTaskStatus(task) }}
                </Badge>
              </div>
              <p class="mt-1 truncate text-xs text-muted-foreground">
                {{ getTaskMeta(task) }}
              </p>
              <p
                v-if="task.description"
                class="mt-1 truncate text-xs text-muted-foreground/70"
              >
                {{ task.description }}
              </p>
            </div>
          </button>
        </div>

        <div class="flex items-center justify-between border-t bg-muted/40 px-4 py-2.5 text-[11px] text-muted-foreground">
          <div class="flex items-center gap-2">
            <Sparkles class="h-3.5 w-3.5" />
            {{ t('tasks.search.footerHint') }}
          </div>
          <div class="hidden items-center gap-2 md:flex">
            <span>{{ t('tasks.search.keyboardUpDown') }}</span>
            <span>{{ t('tasks.search.keyboardEnter') }}</span>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<style scoped>
.search-panel-enter-active,
.search-panel-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.search-panel-enter-from,
.search-panel-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
