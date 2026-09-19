<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import {
  Layers,
  RotateCw,
  ShieldAlert,
  Download,
  Trash2,
  Sparkles,
  Target,
  Eye,
  EyeOff,
  ArrowUpDown,
  ArrowDown,
  ArrowUp,
} from 'lucide-vue-next'

interface FileOption {
  value: string
  label: string
  taskName?: string
}

interface Props {
  files: string[]
  fileOptions?: FileOption[]
  selectedFile: string | null
  aiRecommendedOnly: boolean
  keywordRecommendedOnly: boolean
  includeHidden: boolean
  sortBy: 'crawl_time' | 'publish_time' | 'price' | 'keyword_hit_count'
  sortOrder: 'asc' | 'desc'
  isLoading: boolean
  isReady: boolean
}

const props = defineProps<Props>()
const { t } = useI18n()

const options = computed(() => {
  if (!props.isReady) {
    return []
  }
  if (props.fileOptions && props.fileOptions.length > 0) {
    return props.fileOptions
  }
  return props.files.map((file) => ({ value: file, label: file }))
})

const selectedLabel = computed(() => {
  if (!props.isReady) return t('results.filters.loadingTaskNames')
  if (options.value.length === 0) return t('results.filters.noResults')
  if (!props.selectedFile) return t('results.filters.chooseResult')
  const match = options.value.find((option) => option.value === props.selectedFile)
  return match ? match.label : t('results.filters.taskNameLabel', { task: t('common.unnamed') })
})

const isSelectDisabled = computed(() => !props.isReady || options.value.length === 0)

const isAllMode = computed(() => !props.aiRecommendedOnly && !props.keywordRecommendedOnly)

const emit = defineEmits<{
  (e: 'update:selectedFile', value: string): void
  (e: 'update:aiRecommendedOnly', value: boolean): void
  (e: 'update:keywordRecommendedOnly', value: boolean): void
  (e: 'update:includeHidden', value: boolean): void
  (e: 'update:sortBy', value: 'crawl_time' | 'publish_time' | 'price' | 'keyword_hit_count'): void
  (e: 'update:sortOrder', value: 'asc' | 'desc'): void
  (e: 'refresh'): void
  (e: 'export'): void
  (e: 'delete'): void
  (e: 'manage-blacklist'): void
}>()

function selectAll() {
  emit('update:aiRecommendedOnly', false)
  emit('update:keywordRecommendedOnly', false)
}

function handleToggleAi() {
  if (props.aiRecommendedOnly) {
    emit('update:aiRecommendedOnly', false)
  } else {
    emit('update:aiRecommendedOnly', true)
    emit('update:keywordRecommendedOnly', false)
  }
}

function handleToggleKeyword() {
  if (props.keywordRecommendedOnly) {
    emit('update:keywordRecommendedOnly', false)
  } else {
    emit('update:keywordRecommendedOnly', true)
    emit('update:aiRecommendedOnly', false)
  }
}

function toggleSortOrder() {
  emit('update:sortOrder', props.sortOrder === 'asc' ? 'desc' : 'asc')
}
</script>

<template>
  <div class="rounded-xl border border-border/80 bg-card p-3.5 shadow-sm space-y-3">
    <!-- 第一行：结果集切换与主操作栏 (Cult UI 风格) -->
    <div class="flex flex-col gap-2.5 sm:flex-row sm:items-center sm:justify-between">
      <!-- 结果集选择器 -->
      <div class="flex items-center gap-2 flex-1 max-w-lg">
        <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground">
          <Layers class="h-4 w-4" />
        </div>

        <Select
          :model-value="props.selectedFile || undefined"
          @update:model-value="(value) => emit('update:selectedFile', value as string)"
        >
          <SelectTrigger class="h-9 w-full text-xs font-medium" :disabled="isSelectDisabled">
            <span class="truncate">
              {{ selectedLabel }}
            </span>
          </SelectTrigger>
          <SelectContent>
            <SelectItem v-for="option in options" :key="option.value" :value="option.value" class="text-xs">
              {{ option.label }}
            </SelectItem>
          </SelectContent>
        </Select>
      </div>

      <!-- 右侧动作组 (紧凑图标+文字) -->
      <div class="flex items-center gap-1.5 self-end sm:self-auto">
        <Button
          size="sm"
          variant="outline"
          class="h-8 gap-1 text-xs"
          @click="emit('refresh')"
          :disabled="props.isLoading"
        >
          <RotateCw class="h-3.5 w-3.5" :class="{ 'animate-spin': props.isLoading }" />
          <span>{{ t('common.refresh') }}</span>
        </Button>

        <Button
          size="sm"
          variant="outline"
          class="h-8 gap-1 text-xs"
          @click="emit('manage-blacklist')"
          :disabled="props.isLoading || !props.selectedFile"
        >
          <ShieldAlert class="h-3.5 w-3.5 text-muted-foreground" />
          <span class="hidden sm:inline">{{ t('results.filters.manageBlacklist') }}</span>
        </Button>

        <Button
          size="sm"
          variant="outline"
          class="h-8 gap-1 text-xs"
          @click="emit('export')"
          :disabled="props.isLoading || !props.selectedFile"
        >
          <Download class="h-3.5 w-3.5 text-muted-foreground" />
          <span class="hidden sm:inline">{{ t('results.filters.exportCsv') }}</span>
        </Button>

        <Button
          size="sm"
          variant="ghost"
          class="h-8 gap-1 text-xs text-destructive hover:bg-destructive/10 hover:text-destructive"
          @click="emit('delete')"
          :disabled="props.isLoading || !props.selectedFile"
        >
          <Trash2 class="h-3.5 w-3.5" />
          <span class="hidden sm:inline">{{ t('common.delete') }}</span>
        </Button>
      </div>
    </div>

    <!-- 分割线 -->
    <div class="h-px w-full bg-border/60"></div>

    <!-- 第二行：Commerce UI 风格快速胶囊筛选器 + 排序 -->
    <div class="flex flex-col gap-2.5 sm:flex-row sm:items-center sm:justify-between">
      <!-- 胶囊筛选器 (Segmented Pills) -->
      <div class="flex flex-wrap items-center gap-1.5">
        <!-- 全部商品 -->
        <button
          type="button"
          @click="selectAll"
          class="inline-flex h-7 items-center rounded-md px-2.5 text-xs font-medium transition-colors"
          :class="isAllMode
            ? 'bg-primary text-primary-foreground shadow-sm'
            : 'bg-muted/60 text-muted-foreground hover:bg-muted hover:text-foreground'"
        >
          {{ t('common.all') }}
        </button>

        <!-- 仅看 AI 推荐 -->
        <button
          type="button"
          @click="handleToggleAi"
          class="inline-flex h-7 items-center gap-1 rounded-md px-2.5 text-xs font-medium transition-colors"
          :class="props.aiRecommendedOnly
            ? 'bg-emerald-600 text-white shadow-sm dark:bg-emerald-500'
            : 'bg-muted/60 text-muted-foreground hover:bg-muted hover:text-foreground'"
        >
          <Sparkles class="h-3 w-3" />
          {{ t('results.filters.aiOnly') }}
        </button>

        <!-- 仅看关键词推荐 -->
        <button
          type="button"
          @click="handleToggleKeyword"
          class="inline-flex h-7 items-center gap-1 rounded-md px-2.5 text-xs font-medium transition-colors"
          :class="props.keywordRecommendedOnly
            ? 'bg-blue-600 text-white shadow-sm dark:bg-blue-500'
            : 'bg-muted/60 text-muted-foreground hover:bg-muted hover:text-foreground'"
        >
          <Target class="h-3 w-3" />
          {{ t('results.filters.keywordOnly') }}
        </button>

        <!-- 显示已屏蔽 -->
        <button
          type="button"
          @click="emit('update:includeHidden', !props.includeHidden)"
          class="inline-flex h-7 items-center gap-1 rounded-md px-2 text-xs font-medium transition-colors"
          :class="props.includeHidden
            ? 'border border-border bg-accent text-accent-foreground'
            : 'text-muted-foreground/80 hover:text-foreground'"
        >
          <component :is="props.includeHidden ? Eye : EyeOff" class="h-3 w-3" />
          <span>{{ t('results.filters.includeHidden') }}</span>
        </button>
      </div>

      <!-- 排序组合 (Sort Selector + Asc/Desc) -->
      <div class="flex items-center gap-1.5 self-end sm:self-auto">
        <span class="text-xs text-muted-foreground/80 flex items-center gap-1">
          <ArrowUpDown class="h-3 w-3" />
        </span>

        <Select
          :model-value="props.sortBy"
          @update:model-value="(value) => emit('update:sortBy', value as any)"
        >
          <SelectTrigger class="h-7 w-[110px] text-xs font-medium border-border/80 bg-muted/30">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="crawl_time" class="text-xs">{{ t('results.filters.sortByCrawlTime') }}</SelectItem>
            <SelectItem value="publish_time" class="text-xs">{{ t('results.filters.sortByPublishTime') }}</SelectItem>
            <SelectItem value="price" class="text-xs">{{ t('results.filters.sortByPrice') }}</SelectItem>
            <SelectItem value="keyword_hit_count" class="text-xs">{{ t('results.filters.sortByKeywordHits') }}</SelectItem>
          </SelectContent>
        </Select>

        <button
          type="button"
          @click="toggleSortOrder"
          :title="props.sortOrder === 'desc' ? t('results.filters.desc') : t('results.filters.asc')"
          class="inline-flex h-7 items-center gap-1 rounded-md border border-border/80 bg-muted/30 px-2 text-xs font-medium text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
        >
          <component :is="props.sortOrder === 'desc' ? ArrowDown : ArrowUp" class="h-3 w-3" />
          <span>{{ props.sortOrder === 'desc' ? t('results.filters.desc') : t('results.filters.asc') }}</span>
        </button>
      </div>
    </div>
  </div>
</template>
