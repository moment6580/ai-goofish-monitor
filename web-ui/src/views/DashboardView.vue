<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useDashboard } from '@/composables/useDashboard'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import Badge from '@/components/ui/badge/Badge.vue'
import PriceTrendChart from '@/components/results/PriceTrendChart.vue'
import { formatNumber, formatRelativeTimeFromNow } from '@/i18n'
import {
  Activity,
  ArrowRight,
  Compass,
  Search,
  Sparkles,
  Target,
  Zap,
} from 'lucide-vue-next'

const router = useRouter()
const { t } = useI18n()
const {
  focusInsights,
  focusTask,
  suggestion,
  stats,
  activities,
  isLoading,
  error,
} = useDashboard()

const statCards = computed(() => [
  {
    label: t('dashboard.stats.activeTasks'),
    value: String(stats.value.enabledTasks),
    detail: t('dashboard.stats.runningCount', { count: stats.value.runningTasks }),
    icon: Activity,
    color: 'text-blue-500',
    bg: 'bg-blue-500/10',
  },
  {
    label: t('dashboard.stats.scannedItems'),
    value: formatNumber(stats.value.scannedItems),
    detail: t('dashboard.stats.resultFiles', { count: stats.value.resultFiles }),
    icon: Search,
    color: 'text-emerald-500',
    bg: 'bg-emerald-500/10',
  },
  {
    label: t('dashboard.stats.recommendedItems'),
    value: String(stats.value.recommendedItems),
    detail: t('dashboard.stats.recommendedBreakdown', {
      ai: stats.value.aiRecommendedItems,
      keyword: stats.value.keywordRecommendedItems,
    }),
    icon: Target,
    color: 'text-amber-500',
    bg: 'bg-amber-500/10',
  },
  {
    label: t('dashboard.stats.monitoredTasks'),
    value: String(stats.value.totalTasks),
    detail: t('dashboard.stats.showAllTasks'),
    icon: Compass,
    color: 'text-purple-500',
    bg: 'bg-purple-500/10',
  },
])

const focusTitle = computed(() => focusTask.value?.task_name || t('dashboard.focus.defaultTitle'))
const focusMeta = computed(() => {
  if (!focusTask.value) return t('dashboard.focus.empty')
  const keyword = focusTask.value.keyword || t('dashboard.focus.missingKeyword')
  const count = focusTask.value.total_items
  return t('dashboard.focus.meta', { keyword, count })
})

const insightCards = computed(() => {
  const market = focusInsights.value?.market_summary
  const history = focusInsights.value?.history_summary
  return [
    {
      label: t('results.insights.currentAvg'),
      value: market?.avg_price ? `¥${market.avg_price}` : '—',
      hint: market
        ? t('results.insights.sampleCount', { count: market.sample_count })
        : t('results.grid.empty'),
    },
    {
      label: t('results.insights.historyAvg'),
      value: history?.avg_price ? `¥${history.avg_price}` : '—',
      hint: history
        ? t('results.insights.uniqueItems', { count: history.unique_items })
        : t('results.insights.noSnapshot'),
    },
    {
      label: t('results.card.marketAvg'),
      value: market?.min_price ? `¥${market.min_price}` : '—',
      hint: market?.max_price
        ? t('results.insights.highestPrice', { price: market.max_price })
        : t('results.insights.noRange'),
    },
  ]
})

function goCreateTask() {
  router.push({
    name: 'Tasks',
    query: { create: '1' },
  })
}

function openSuggestion() {
  router.push({
    name: suggestion.value.routeName,
    query: suggestion.value.query,
  })
}

function openActivity(activity: { filename: string | null; type: string }) {
  if (activity.filename) {
    router.push({ name: 'Results', query: { file: activity.filename } })
    return
  }
  if (activity.type === 'task') {
    router.push({ name: 'Tasks' })
    return
  }
  router.push({ name: 'Dashboard' })
}
</script>

<template>
  <div class="space-y-6">
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
      <div>
        <h1 class="text-2xl font-semibold tracking-tight">{{ t('dashboard.title') }}</h1>
        <p class="mt-1 text-sm text-muted-foreground">
          {{ t('dashboard.description') }}
        </p>
      </div>
      <div class="flex items-center gap-3">
        <Button @click="goCreateTask">
          {{ t('dashboard.createTask') }}
        </Button>
      </div>
    </div>
    <div v-if="error" class="app-alert-error" role="alert">
      {{ error.message }}
    </div>
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <Card v-for="stat in statCards" :key="stat.label" class="shadow-card">
        <CardContent class="p-6">
          <div class="flex items-center justify-between">
            <div class="space-y-1.5">
              <p class="text-sm text-muted-foreground">{{ stat.label }}</p>
              <h3 class="text-2xl font-semibold tracking-tight">{{ stat.value }}</h3>
            </div>
            <div :class="[stat.bg, 'p-2.5 rounded-lg']">
              <component :is="stat.icon" :class="['h-5 w-5', stat.color]" />
            </div>
          </div>
          <div class="mt-3 text-xs text-muted-foreground">
            {{ stat.detail }}
          </div>
        </CardContent>
      </Card>
    </div>
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <Card class="lg:col-span-2">
        <CardHeader class="flex flex-col gap-2 border-b pb-4 md:flex-row md:items-start md:justify-between">
          <div class="space-y-1.5">
            <CardTitle class="text-base font-semibold">
              {{ focusTitle }}
            </CardTitle>
            <p class="text-sm text-muted-foreground">{{ focusMeta }}</p>
          </div>
          <Badge variant="secondary" class="w-fit font-normal">
            {{ focusTask?.latest_crawl_time ? t('dashboard.focus.latestUpdate', { time: formatRelativeTimeFromNow(focusTask.latest_crawl_time) }) : t('dashboard.focus.waiting') }}
          </Badge>
        </CardHeader>
        <CardContent class="space-y-6 p-6">
          <div v-if="isLoading" class="rounded-lg border border-dashed px-4 py-10 text-center text-sm text-muted-foreground">
            {{ t('dashboard.focus.loading') }}
          </div>
          <div v-else-if="!focusTask?.filename" class="rounded-lg border border-dashed px-4 py-10 text-center text-sm text-muted-foreground">
            {{ t('dashboard.focus.noResults') }}
          </div>
          <template v-else>
            <div class="grid gap-4 md:grid-cols-3">
              <article
                v-for="card in insightCards"
                :key="card.label"
                class="rounded-lg border bg-muted/40 p-4"
              >
                <p class="text-xs text-muted-foreground">{{ card.label }}</p>
                <p class="mt-2 text-xl font-semibold tracking-tight">{{ card.value }}</p>
                <p class="mt-1.5 text-xs text-muted-foreground">{{ card.hint }}</p>
              </article>
            </div>
            <PriceTrendChart :points="focusInsights?.daily_trend || []" />
            <div class="grid gap-3 rounded-lg border p-4 md:grid-cols-3">
              <div class="rounded-md bg-muted/50 px-3 py-2.5 text-sm text-muted-foreground">
                {{ t('dashboard.focus.currentMedian') }}
                <span class="font-medium text-foreground">
                  {{ focusInsights?.market_summary.median_price ? `¥${focusInsights.market_summary.median_price}` : '—' }}
                </span>
              </div>
              <div class="rounded-md bg-muted/50 px-3 py-2.5 text-sm text-muted-foreground">
                {{ t('dashboard.focus.historyMin') }}
                <span class="font-medium text-foreground">
                  {{ focusInsights?.history_summary.min_price ? `¥${focusInsights.history_summary.min_price}` : '—' }}
                </span>
              </div>
              <div class="rounded-md bg-muted/50 px-3 py-2.5 text-sm text-muted-foreground">
                {{ t('dashboard.focus.historyMax') }}
                <span class="font-medium text-foreground">
                  {{ focusInsights?.history_summary.max_price ? `¥${focusInsights.history_summary.max_price}` : '—' }}
                </span>
              </div>
            </div>
          </template>
        </CardContent>
      </Card>
      <div class="space-y-6">
        <Card>
          <CardHeader class="pb-4">
            <CardTitle class="text-base font-semibold flex items-center gap-2">
              <Activity class="h-4 w-4 text-muted-foreground" />
              {{ t('dashboard.activity.title') }}
            </CardTitle>
          </CardHeader>
          <CardContent class="p-0">
            <div v-if="activities.length === 0" class="px-6 pb-6 pt-1 text-sm text-muted-foreground">
              {{ t('dashboard.activity.empty') }}
            </div>
            <div v-else class="divide-y divide-border">
              <button
                v-for="activity in activities"
                :key="activity.id"
                class="w-full p-4 text-left transition-colors hover:bg-muted/50"
                @click="openActivity(activity)"
              >
                <div class="flex items-center justify-between gap-3">
                  <div class="flex items-center gap-3 min-w-0">
                    <div class="h-2 w-2 shrink-0 rounded-full bg-success"></div>
                    <div class="min-w-0">
                      <p class="text-sm font-medium truncate">{{ activity.title }}</p>
                      <p class="mt-0.5 text-xs text-muted-foreground">
                        {{ activity.task_name }} · {{ formatRelativeTimeFromNow(activity.timestamp) }}
                      </p>
                      <p v-if="activity.detail" class="mt-1 text-xs text-muted-foreground/80 truncate">{{ activity.detail }}</p>
                    </div>
                  </div>
                  <Badge variant="outline" class="shrink-0 font-normal text-muted-foreground">
                    {{ activity.status }}
                  </Badge>
                </div>
              </button>
            </div>
            <button
              class="flex w-full items-center justify-center gap-2 border-t py-2.5 text-xs font-medium text-muted-foreground transition-colors hover:bg-muted/50 hover:text-foreground"
              @click="router.push({ name: 'Logs' })"
            >
              {{ t('dashboard.activity.viewAllLogs') }}
              <ArrowRight class="h-3 w-3" />
            </button>
          </CardContent>
        </Card>
        <Card>
          <CardHeader class="pb-3">
            <CardTitle class="flex items-center gap-2 text-base font-semibold">
              <Zap class="h-4 w-4 text-muted-foreground" />
              {{ t('dashboard.suggestion.sectionTitle') }}
            </CardTitle>
          </CardHeader>
          <CardContent class="space-y-4">
            <p class="text-sm leading-relaxed">{{ suggestion.title }}</p>
            <p class="text-sm leading-relaxed text-muted-foreground">{{ suggestion.description }}</p>
            <Button variant="secondary" class="w-full" @click="openSuggestion">
              <Sparkles class="mr-2 h-4 w-4" />
              {{ suggestion.actionLabel }}
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  </div>
</template>
