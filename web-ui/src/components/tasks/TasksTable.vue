<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import type { Task } from '@/types/task.d.ts'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { Badge } from '@/components/ui/badge'
import {
  Play,
  Square,
  Pencil,
  Trash2,
  Keyboard,
  Clock,
  Layers,
  MapPin,
  RefreshCcw,
  Search
} from 'lucide-vue-next'
import { formatCountdown, formatNextRunAbsolute } from '@/lib/taskSchedule'

interface Props {
  tasks: Task[]
  isLoading: boolean
  stoppingIds?: Set<number>
}

const props = defineProps<Props>()
const { t } = useI18n()
const isStopping = (id: number) => props.stoppingIds?.has(id) ?? false
const isKeywordMode = (task: Task) => task.decision_mode === 'keyword'
const nowMs = ref(Date.now())
let timer: number | null = null

onMounted(() => {
  timer = window.setInterval(() => {
    nowMs.value = Date.now()
  }, 1000)
})

onBeforeUnmount(() => {
  if (timer !== null) {
    window.clearInterval(timer)
  }
})

const resolveAccountStrategyLabel = (task: Task) => {
  if (task.account_strategy === 'rotate') return t('tasks.table.accountRotate')
  if (task.account_strategy === 'fixed') return t('tasks.table.accountFixed')
  return t('tasks.table.accountAuto')
}

const resolveAccountName = (task: Task) => {
  if (!task.account_state_file) return t('tasks.table.systemSelected')
  const segments = task.account_state_file.split('/')
  const filename = segments[segments.length - 1] || task.account_state_file
  return filename.replace('.json', '')
}

const resolveCountdownText = (task: Task) => {
  if (!task.cron) return t('tasks.table.manualTrigger')
  if (!task.enabled) return t('tasks.table.disabled')
  return formatCountdown(task.next_run_at, nowMs.value) || t('tasks.table.waitingSchedule')
}

const resolveCountdownTone = (task: Task) => {
  if (!task.cron || !task.enabled) return 'text-muted-foreground'
  return 'text-foreground'
}

const resolveNextRunLabel = (task: Task) => {
  if (!task.cron || !task.enabled || !task.next_run_at) return null
  return formatNextRunAbsolute(task.next_run_at)
}

const emit = defineEmits<{
  (e: 'delete-task', taskId: number): void
  (e: 'run-task', taskId: number): void
  (e: 'stop-task', taskId: number): void
  (e: 'edit-task', task: Task): void
  (e: 'refresh-criteria', task: Task): void
  (e: 'toggle-enabled', task: Task, enabled: boolean): void
}>()
</script>

<template>
  <div class="overflow-hidden rounded-lg border bg-card">
    <!-- 移动端卡片 -->
    <div class="space-y-3 p-4 lg:hidden">
      <template v-if="isLoading && tasks.length === 0">
        <div class="flex min-h-40 flex-col items-center justify-center gap-2 text-muted-foreground">
          <RefreshCcw class="h-5 w-5 animate-spin" />
          <span class="text-sm">{{ t('tasks.table.syncing') }}</span>
        </div>
      </template>
      <template v-else-if="tasks.length === 0">
        <div class="flex min-h-40 flex-col items-center justify-center gap-2 text-muted-foreground">
          <Layers class="h-10 w-10 opacity-30" />
          <p class="text-sm font-medium">{{ t('tasks.table.empty') }}</p>
        </div>
      </template>
      <template v-else>
        <article
          v-for="task in tasks"
          :key="task.id"
          class="rounded-lg border bg-background p-4"
        >
          <div class="flex items-start justify-between gap-3">
            <div class="min-w-0 space-y-1.5">
              <div class="flex flex-wrap items-center gap-2">
                <h3 class="truncate text-sm font-semibold tracking-tight">
                  {{ task.task_name }}
                </h3>
                <Badge variant="secondary" class="font-normal text-muted-foreground">
                  <component :is="isKeywordMode(task) ? Keyboard : Search" class="mr-1 h-3 w-3" />
                  {{ isKeywordMode(task) ? 'KEYWORD' : 'AI' }}
                </Badge>
              </div>

              <div class="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
                <div class="inline-flex items-center gap-1.5 rounded-md bg-muted px-2 py-0.5 text-xs font-medium">
                  <Search class="h-3 w-3" />
                  {{ task.keyword }}
                </div>
                <span v-if="task.description" class="line-clamp-1 text-xs">
                  {{ task.description }}
                </span>
              </div>
            </div>

            <div class="flex flex-col items-end gap-2">
              <Switch
                :model-value="task.enabled"
                @update:model-value="(val: boolean) => emit('toggle-enabled', task, val)"
              />
              <Badge
                variant="outline"
                class="font-normal"
                :class="task.is_running ? 'border-success/40 text-success' : 'text-muted-foreground'"
              >
                {{ task.is_running ? t('common.running') : t('common.idle') }}
              </Badge>
            </div>
          </div>

          <div class="mt-4 grid gap-3 sm:grid-cols-2">
            <div class="rounded-md bg-muted/40 p-3">
              <p class="text-xs text-muted-foreground">
                {{ t('tasks.table.headers.crawl') }}
              </p>
              <p class="mt-1.5 text-sm font-medium tabular-nums">
                ¥{{ task.min_price || 0 }} - {{ task.max_price || 'MAX' }}
              </p>
              <div class="mt-2 flex flex-wrap gap-1.5">
                <Badge variant="secondary" class="font-normal text-muted-foreground">
                  {{ task.personal_only ? t('tasks.table.personalOnly') : t('common.all') }}
                </Badge>
                <Badge variant="secondary" class="font-normal text-muted-foreground">
                  {{ task.free_shipping ? t('tasks.table.freeShipping') : t('common.all') }}
                </Badge>
                <Badge v-if="task.region" variant="secondary" class="font-normal text-muted-foreground">
                  <MapPin class="mr-1 h-3 w-3" />
                  {{ task.region }}
                </Badge>
              </div>
            </div>

            <div class="rounded-md bg-muted/40 p-3">
              <p class="text-xs text-muted-foreground">
                {{ t('tasks.table.headers.schedule') }}
              </p>
              <p class="mt-1.5 text-sm font-medium" :class="resolveCountdownTone(task)">
                {{ resolveCountdownText(task) }}
              </p>
              <div class="mt-2 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                <span class="inline-flex items-center gap-1">
                  <Clock class="h-3 w-3" />
                  {{ task.cron || 'MANUAL' }}
                </span>
                <span class="inline-flex items-center gap-1">
                  <Layers class="h-3 w-3" />
                  {{ task.max_pages || 3 }}P
                </span>
              </div>
            </div>

            <div class="rounded-md bg-muted/40 p-3 sm:col-span-2">
              <div class="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <p class="text-xs text-muted-foreground">
                    {{ t('tasks.table.headers.mode') }}
                  </p>
                  <p class="mt-1.5 text-sm font-medium">
                    {{ resolveAccountStrategyLabel(task) }} · {{ resolveAccountName(task) }}
                  </p>
                </div>

                <div v-if="isKeywordMode(task)" class="text-xs text-muted-foreground">
                  {{ t('tasks.table.keywordStrategies', { count: task.keyword_rules?.length || 0 }) }}
                </div>
                <div v-else class="flex flex-wrap items-center gap-2">
                  <Badge variant="outline" class="max-w-[200px] truncate font-mono font-normal text-muted-foreground">
                    {{ (task.ai_prompt_criteria_file || 'STANDARD').split('/').pop() }}
                  </Badge>
                  <Button
                    size="sm"
                    variant="ghost"
                    :aria-label="`${t('tasks.table.refreshCriteria')} ${task.task_name}`"
                    @click="emit('refresh-criteria', task)"
                  >
                    <RefreshCcw class="mr-1 h-3.5 w-3.5" />
                    {{ t('tasks.table.refreshCriteria') }}
                  </Button>
                </div>
              </div>
            </div>
          </div>

          <div class="mt-4 flex flex-wrap gap-2">
            <Button
              v-if="!task.is_running"
              size="sm"
              class="flex-1 min-w-[120px]"
              :class="task.enabled ? '' : 'pointer-events-none opacity-50'"
              :aria-label="`${t('tasks.table.start')} ${task.task_name}`"
              @click="emit('run-task', task.id)"
            >
              <Play class="mr-1 h-3.5 w-3.5 fill-current" />
              {{ t('tasks.table.start') }}
            </Button>
            <Button
              v-else
              size="sm"
              variant="destructive"
              class="flex-1 min-w-[120px]"
              :disabled="isStopping(task.id)"
              :aria-label="`${t('tasks.table.stop')} ${task.task_name}`"
              @click="emit('stop-task', task.id)"
            >
              <Square v-if="!isStopping(task.id)" class="mr-1 h-3.5 w-3.5 fill-current" />
              <RefreshCcw v-else class="mr-1 h-3.5 w-3.5 animate-spin" />
              {{ isStopping(task.id) ? t('tasks.table.stopping') : t('tasks.table.stop') }}
            </Button>
            <Button
              size="icon"
              variant="outline"
              class="size-9"
              :aria-label="`${t('common.edit')} ${task.task_name}`"
              @click="emit('edit-task', task)"
            >
              <Pencil class="h-4 w-4" />
            </Button>
            <Button
              size="icon"
              variant="outline"
              class="size-9 text-destructive hover:bg-destructive/10 hover:text-destructive"
              :aria-label="`${t('common.delete')} ${task.task_name}`"
              @click="emit('delete-task', task.id)"
            >
              <Trash2 class="h-4 w-4" />
            </Button>
          </div>
        </article>
      </template>
    </div>

    <!-- 桌面端表格 -->
    <div class="hidden lg:block">
      <Table>
        <TableHeader>
          <TableRow class="hover:bg-transparent">
            <TableHead class="w-[90px] px-6 text-center">{{ t('tasks.table.headers.status') }}</TableHead>
            <TableHead class="min-w-[280px]">{{ t('tasks.table.headers.details') }}</TableHead>
            <TableHead class="w-[170px]">{{ t('tasks.table.headers.crawl') }}</TableHead>
            <TableHead class="w-[170px] text-center">{{ t('tasks.table.headers.mode') }}</TableHead>
            <TableHead class="w-[140px] text-center">{{ t('tasks.table.headers.schedule') }}</TableHead>
            <TableHead class="w-[170px] px-6 text-right">{{ t('tasks.table.headers.actions') }}</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <template v-if="isLoading && tasks.length === 0">
            <TableRow>
              <TableCell :colspan="6" class="h-32 text-center">
                <div class="flex flex-col items-center justify-center gap-2 text-muted-foreground">
                  <RefreshCcw class="h-5 w-5 animate-spin" />
                  <span class="text-sm">{{ t('tasks.table.syncing') }}</span>
                </div>
              </TableCell>
            </TableRow>
          </template>
          <template v-else-if="tasks.length === 0">
            <TableRow>
              <TableCell :colspan="6" class="h-40 text-center">
                <div class="flex flex-col items-center justify-center gap-2 text-muted-foreground">
                  <Layers class="h-10 w-10 opacity-30" />
                  <p class="text-sm font-medium">{{ t('tasks.table.empty') }}</p>
                </div>
              </TableCell>
            </TableRow>
          </template>
          <template v-else>
            <TableRow
              v-for="task in tasks"
              :key="task.id"
              class="group"
            >
              <!-- 状态 -->
              <TableCell class="px-6 align-middle">
                <div class="flex flex-col items-center gap-2">
                  <Switch
                    :model-value="task.enabled"
                    @update:model-value="(val: boolean) => emit('toggle-enabled', task, val)"
                  />
                  <span
                    class="inline-flex items-center gap-1.5 text-xs"
                    :class="task.is_running ? 'text-success' : 'text-muted-foreground'"
                  >
                    <span
                      class="h-1.5 w-1.5 rounded-full"
                      :class="task.is_running ? 'bg-success' : 'bg-muted-foreground/40'"
                    ></span>
                    {{ task.is_running ? t('common.running') : t('common.idle') }}
                  </span>
                </div>
              </TableCell>

              <!-- 任务信息 -->
              <TableCell class="align-middle">
                <div class="flex flex-col gap-1.5 py-1">
                  <div class="flex items-center gap-2">
                    <span class="text-sm font-medium">{{ task.task_name }}</span>
                    <Badge variant="secondary" class="font-normal text-muted-foreground">
                      <component :is="isKeywordMode(task) ? Keyboard : Search" class="mr-1 h-3 w-3" />
                      {{ isKeywordMode(task) ? 'KEYWORD' : 'AI' }}
                    </Badge>
                  </div>

                  <div class="flex items-center gap-2">
                    <div class="flex items-center gap-1.5 rounded-md bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">
                      <Search class="h-3 w-3" /> {{ task.keyword }}
                    </div>
                    <div
                      v-if="task.description"
                      class="line-clamp-1 max-w-[180px] text-xs text-muted-foreground/80"
                      :title="task.description"
                    >
                      {{ task.description }}
                    </div>
                  </div>

                  <div class="flex items-center gap-2 text-xs text-muted-foreground/70">
                    <span>{{ resolveAccountStrategyLabel(task) }}</span>
                    <span class="truncate max-w-[120px]">{{ resolveAccountName(task) }}</span>
                  </div>
                </div>
              </TableCell>

              <!-- 抓取配置 -->
              <TableCell class="align-middle text-left">
                <div class="space-y-1.5">
                  <div class="text-sm font-medium tabular-nums">
                    ¥{{ task.min_price || 0 }} <span class="font-normal text-muted-foreground">-</span> {{ task.max_price || 'MAX' }}
                  </div>
                  <div class="flex flex-wrap gap-1">
                    <Badge variant="secondary" class="font-normal text-muted-foreground">
                      {{ task.personal_only ? t('tasks.table.personalOnly') : t('common.all') }}
                    </Badge>
                    <Badge variant="secondary" class="font-normal text-muted-foreground">
                      {{ task.free_shipping ? t('tasks.table.freeShipping') : t('common.all') }}
                    </Badge>
                    <Badge
                      v-if="task.region"
                      variant="secondary"
                      class="max-w-[90px] truncate font-normal text-muted-foreground"
                    >
                      <MapPin class="mr-1 h-3 w-3" /> {{ task.region }}
                    </Badge>
                  </div>
                </div>
              </TableCell>

              <!-- 模式详情 -->
              <TableCell class="align-middle text-center">
                <div class="inline-flex flex-col items-center gap-1.5">
                  <div v-if="isKeywordMode(task)" class="text-xs text-muted-foreground">
                    {{ t('tasks.table.keywordStrategies', { count: task.keyword_rules?.length || 0 }) }}
                  </div>
                  <template v-else>
                    <Badge
                      variant="outline"
                      class="max-w-[150px] truncate font-mono font-normal text-muted-foreground"
                      :title="task.ai_prompt_criteria_file"
                    >
                      {{ (task.ai_prompt_criteria_file || 'STANDARD').split('/').pop() }}
                    </Badge>
                    <Button
                      size="sm"
                      variant="ghost"
                      class="h-7 px-2 text-xs text-muted-foreground"
                      :aria-label="`${t('tasks.table.refreshCriteria')} ${task.task_name}`"
                      :title="`${t('tasks.table.refreshCriteria')} ${task.task_name}`"
                      @click="emit('refresh-criteria', task)"
                    >
                      <RefreshCcw class="mr-1 h-3 w-3" /> {{ t('tasks.table.refreshCriteria') }}
                    </Button>
                  </template>
                </div>
              </TableCell>

              <!-- 调度 -->
              <TableCell class="align-middle text-center">
                <div class="inline-flex flex-col items-center gap-1">
                  <div class="inline-flex items-center gap-1 text-xs text-muted-foreground">
                    <Clock class="h-3 w-3" />
                    <span class="font-mono">{{ task.cron || 'MANUAL' }}</span>
                  </div>
                  <div
                    class="text-xs font-medium"
                    :class="resolveCountdownTone(task)"
                    :title="resolveNextRunLabel(task) || undefined"
                  >
                    {{ resolveCountdownText(task) }}
                  </div>
                  <div class="flex items-center gap-1 text-xs text-muted-foreground/70">
                    <Layers class="h-3 w-3" /> {{ task.max_pages || 3 }}P
                  </div>
                </div>
              </TableCell>

              <!-- 操作 -->
              <TableCell class="px-6 align-middle text-right">
                <div class="flex items-center justify-end gap-1.5">
                  <Button
                    v-if="!task.is_running"
                    size="sm"
                    variant="outline"
                    class="h-8"
                    :class="task.enabled ? '' : 'pointer-events-none opacity-50'"
                    :aria-label="`${t('tasks.table.start')} ${task.task_name}`"
                    @click="emit('run-task', task.id)"
                  >
                    <Play class="mr-1 h-3 w-3 fill-current" />
                    {{ t('tasks.table.start') }}
                  </Button>
                  <Button
                    v-else
                    size="sm"
                    variant="outline"
                    class="h-8 text-destructive hover:bg-destructive/10 hover:text-destructive"
                    :disabled="isStopping(task.id)"
                    :aria-label="`${t('tasks.table.stop')} ${task.task_name}`"
                    @click="emit('stop-task', task.id)"
                  >
                    <Square v-if="!isStopping(task.id)" class="mr-1 h-3 w-3 fill-current" />
                    <RefreshCcw v-else class="mr-1 h-3 w-3 animate-spin" />
                    {{ isStopping(task.id) ? t('tasks.table.stopping') : t('tasks.table.stop') }}
                  </Button>

                  <Button
                    size="icon"
                    variant="ghost"
                    class="h-8 w-8 text-muted-foreground hover:text-foreground"
                    :aria-label="`${t('common.edit')} ${task.task_name}`"
                    :title="`${t('common.edit')} ${task.task_name}`"
                    @click="emit('edit-task', task)"
                  >
                    <Pencil class="h-3.5 w-3.5" />
                  </Button>
                  <Button
                    size="icon"
                    variant="ghost"
                    class="h-8 w-8 text-muted-foreground hover:text-destructive"
                    :aria-label="`${t('common.delete')} ${task.task_name}`"
                    :title="`${t('common.delete')} ${task.task_name}`"
                    @click="emit('delete-task', task.id)"
                  >
                    <Trash2 class="h-3.5 w-3.5" />
                  </Button>
                </div>
              </TableCell>
            </TableRow>
          </template>
        </TableBody>
      </Table>
    </div>
  </div>
</template>

<style scoped>
:deep(td) {
  @apply py-3 px-4;
}
:deep(th) {
  @apply h-10 px-4;
}
</style>
