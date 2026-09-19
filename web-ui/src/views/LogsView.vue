<script setup lang="ts">
import { ref, watch, nextTick, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useLogs } from '@/composables/useLogs'
import { useTasks } from '@/composables/useTasks'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import { Card, CardContent } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { toast } from '@/components/ui/toast'
import {
  Terminal,
  RotateCw,
  Trash2,
  ArrowDown,
} from 'lucide-vue-next'

const { t } = useI18n()
const { tasks } = useTasks()
const {
  logs,
  isAutoRefresh,
  clearLogs,
  toggleAutoRefresh,
  fetchLogs,
  setTaskId,
  loadLatest,
  loadPrevious,
  isFetchingHistory,
  hasMoreHistory,
} = useLogs()

const logContainer = ref<HTMLElement | null>(null)
const autoScroll = ref(true)
const isClearDialogOpen = ref(false)
const selectedTaskId = ref('')
const isPrepending = ref(false)
const lastScrollTop = ref(0)
const lastScrollHeight = ref(0)

const selectedTask = computed(() => {
  if (!selectedTaskId.value) return null
  return tasks.value.find((task) => String(task.id) === selectedTaskId.value) || null
})

const selectedTaskName = computed(() => selectedTask.value?.task_name || '')

// Auto-scroll logic
watch(logs, async () => {
  if (isPrepending.value) {
    await nextTick()
    if (logContainer.value) {
      const delta = logContainer.value.scrollHeight - lastScrollHeight.value
      logContainer.value.scrollTop = lastScrollTop.value + delta
    }
    isPrepending.value = false
    return
  }
  if (autoScroll.value) {
    await nextTick()
    scrollToBottom()
  }
})

watch(tasks, (list) => {
  if (!list.length) {
    selectedTaskId.value = ''
    setTaskId(null)
    return
  }
  if (selectedTaskId.value && list.some((task) => String(task.id) === selectedTaskId.value)) {
    return
  }
  const running = list.find((task) => task.is_running)
  const fallback = list[0]
  if (!fallback) {
    selectedTaskId.value = ''
    setTaskId(null)
    return
  }
  selectedTaskId.value = String(running ? running.id : fallback.id)
}, { immediate: true })

watch(selectedTaskId, (taskId) => {
  const resolvedTaskId = taskId ? Number(taskId) : null
  setTaskId(resolvedTaskId)
  if (resolvedTaskId) {
    loadLatest(50)
  }
})

function scrollToBottom() {
  if (logContainer.value) {
    logContainer.value.scrollTop = logContainer.value.scrollHeight
  }
}

async function handleScroll() {
  if (!logContainer.value) return
  if (!hasMoreHistory.value || isFetchingHistory.value) return
  if (logContainer.value.scrollTop > 120) return
  lastScrollTop.value = logContainer.value.scrollTop
  lastScrollHeight.value = logContainer.value.scrollHeight
  isPrepending.value = true
  await loadPrevious(50)
}

function openClearDialog() {
  isClearDialogOpen.value = true
}

async function handleClearLogs() {
  try {
    await clearLogs()
    toast({ title: t('logs.logsCleared') })
  } catch (e) {
    toast({
      title: t('logs.clearFailed'),
      description: (e as Error).message,
      variant: 'destructive',
    })
  } finally {
    isClearDialogOpen.value = false
  }
}
</script>

<template>
  <div class="flex h-[calc(100vh-100px)] flex-col gap-3">
    <!-- 顶部控制栏 (Kibo UI 风格) -->
    <div class="rounded-xl border border-border/80 bg-card p-3 shadow-xs">
      <div class="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
        <!-- 任务选择与标题 -->
        <div class="flex flex-wrap items-center gap-3">
          <div class="flex items-center gap-2">
            <div class="flex h-7 w-7 items-center justify-center rounded-md bg-primary/10 text-primary">
              <Terminal class="h-4 w-4" />
            </div>
            <h1 class="text-base font-semibold tracking-tight">{{ t('logs.title') }}</h1>
          </div>

          <div class="h-4 w-px bg-border/60 hidden sm:block"></div>

          <div class="flex items-center gap-2">
            <Select v-model="selectedTaskId">
              <SelectTrigger class="h-8 w-full sm:w-[240px] text-xs font-medium">
                <SelectValue :placeholder="t('logs.selectTask')" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem v-for="task in tasks" :key="task.id" :value="String(task.id)" class="text-xs">
                  {{ task.task_name }}{{ task.is_running ? t('logs.taskRunningSuffix') : '' }}
                </SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        <!-- 动作与开关组 -->
        <div class="flex flex-wrap items-center gap-2 sm:justify-end text-xs">
          <Button
            variant="outline"
            size="sm"
            class="h-7 text-xs gap-1"
            :disabled="!selectedTaskId"
            @click="fetchLogs"
          >
            <RotateCw class="h-3 w-3" />
            <span>{{ t('common.refresh') }}</span>
          </Button>

          <div class="flex items-center space-x-1.5 px-1.5">
            <Switch
              id="auto-refresh"
              :model-value="isAutoRefresh"
              class="scale-90"
              @update:model-value="toggleAutoRefresh"
            />
            <Label for="auto-refresh" class="text-xs cursor-pointer text-muted-foreground">{{ t('logs.autoRefresh') }}</Label>
          </div>

          <div class="flex items-center space-x-1.5 px-1.5">
            <Switch
              id="auto-scroll"
              v-model="autoScroll"
              class="scale-90"
            />
            <Label for="auto-scroll" class="text-xs cursor-pointer text-muted-foreground">{{ t('logs.autoScroll') }}</Label>
          </div>

          <Button
            variant="ghost"
            size="sm"
            class="h-7 text-xs text-destructive hover:bg-destructive/10 hover:text-destructive gap-1"
            :disabled="!selectedTaskId"
            @click="openClearDialog"
          >
            <Trash2 class="h-3 w-3" />
            <span>{{ t('logs.clearLogs') }}</span>
          </Button>
        </div>
      </div>
    </div>

    <!-- 终端视窗 (Kibo UI 极客控制台风格) -->
    <Card class="flex flex-1 flex-col overflow-hidden rounded-xl border border-zinc-800 bg-zinc-950 shadow-sm">
      <!-- 仿终端窗口标题栏 -->
      <div class="flex h-8 shrink-0 items-center justify-between border-b border-zinc-800/80 bg-zinc-900/90 px-3 text-[11px] text-zinc-400">
        <div class="flex items-center gap-1.5">
          <span class="h-2.5 w-2.5 rounded-full bg-rose-500/80"></span>
          <span class="h-2.5 w-2.5 rounded-full bg-amber-500/80"></span>
          <span class="h-2.5 w-2.5 rounded-full bg-emerald-500/80"></span>
          <span class="ml-2 font-mono text-zinc-400 font-medium">spider_console — {{ selectedTaskName || 'stdout' }}</span>
        </div>

        <div class="flex items-center gap-2 font-mono text-[10px] text-zinc-500">
          <span v-if="isAutoRefresh" class="flex items-center gap-1 text-emerald-400">
            <span class="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
            LIVE
          </span>
          <span>UTF-8</span>
        </div>
      </div>

      <!-- 日志流主体 -->
      <CardContent class="relative flex-1 p-0">
        <pre
          ref="logContainer"
          @scroll="handleScroll"
          class="absolute inset-0 overflow-auto whitespace-pre-wrap break-all p-4 font-mono text-xs leading-relaxed text-zinc-200 selection:bg-zinc-800 selection:text-white"
        >{{ logs || 'Waiting for spider output...' }}</pre>

        <!-- 自动滚动恢复提示悬浮按钮 -->
        <button
          v-if="!autoScroll && logs"
          type="button"
          @click="scrollToBottom(); autoScroll = true"
          class="absolute bottom-3 right-4 flex items-center gap-1 rounded-full border border-zinc-700 bg-zinc-900/90 px-2.5 py-1 text-[11px] text-zinc-300 shadow-md backdrop-blur-sm transition-all hover:bg-zinc-800"
        >
          <ArrowDown class="h-3 w-3 animate-bounce" />
          滚动至最新
        </button>
      </CardContent>
    </Card>

    <!-- 清理确认弹窗 -->
    <Dialog v-model:open="isClearDialogOpen">
      <DialogContent class="sm:max-w-[400px]">
        <DialogHeader>
          <DialogTitle>{{ t('logs.dialogTitle') }}</DialogTitle>
          <DialogDescription>
            {{ t('logs.dialogDescription') }}
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" size="sm" @click="isClearDialogOpen = false">{{ t('common.cancel') }}</Button>
          <Button variant="destructive" size="sm" @click="handleClearLogs">{{ t('logs.confirmClear') }}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>
