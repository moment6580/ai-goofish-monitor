<script setup lang="ts">
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { ResultInsights } from '@/types/result.d.ts'
import PriceTrendChart from './PriceTrendChart.vue'
import { formatDateTime } from '@/i18n'
import { Button } from '@/components/ui/button'
import Badge from '@/components/ui/badge/Badge.vue'
import {
  LineChart,
  ChevronDown,
  ChevronUp,
  Sparkles,
} from 'lucide-vue-next'

const props = defineProps<{
  insights: ResultInsights | null
  selectedTaskLabel?: string | null
}>()
const { t } = useI18n()
const isCollapsed = ref(false)

const summaryCards = computed(() => {
  if (!props.insights) return []
  const market = props.insights.market_summary
  const history = props.insights.history_summary
  return [
    {
      label: t('results.insights.currentAvg'),
      value: market.avg_price ? `¥${market.avg_price}` : '—',
      hint: t('results.insights.sampleCount', { count: market.sample_count || 0 }),
    },
    {
      label: t('results.insights.historyAvg'),
      value: history.avg_price ? `¥${history.avg_price}` : '—',
      hint: t('results.insights.uniqueItems', { count: history.unique_items || 0 }),
    },
    {
      label: t('results.insights.currentMin'),
      value: market.min_price ? `¥${market.min_price}` : '—',
      hint: market.max_price
        ? t('results.insights.highestPrice', { price: market.max_price })
        : t('results.insights.noRange'),
    },
  ]
})

const latestSnapshotText = computed(() => {
  if (!props.insights?.latest_snapshot_at) return t('results.insights.noSnapshot')
  return t('results.insights.latestSnapshot', {
    time: formatDateTime(props.insights.latest_snapshot_at, {
      dateStyle: 'medium',
      timeStyle: 'short',
    }),
  })
})
</script>

<template>
  <section class="overflow-hidden rounded-xl border border-border/80 bg-card shadow-sm transition-all">
    <!-- 面板标题与折叠栏 (Cult UI 风格) -->
    <div class="flex items-center justify-between px-4 py-3 border-b border-border/60 bg-muted/20">
      <div class="flex items-center gap-2.5">
        <div class="flex h-7 w-7 items-center justify-center rounded-md bg-primary/10 text-primary">
          <LineChart class="h-4 w-4" />
        </div>
        <div>
          <div class="flex items-center gap-2">
            <h2 class="text-sm font-semibold tracking-tight">
              {{ selectedTaskLabel || t('results.insights.defaultTitle') }}
            </h2>
            <Badge variant="outline" class="text-[10px] px-1.5 py-0 h-4 font-normal text-muted-foreground">
              {{ t('results.insights.panelBadge') }}
            </Badge>
          </div>
        </div>
      </div>

      <div class="flex items-center gap-2">
        <span
          v-if="insights?.market_summary.sample_count"
          class="hidden sm:inline-flex text-xs text-muted-foreground"
        >
          {{ t('results.insights.sampleTotal', { count: insights.market_summary.sample_count }) }}
        </span>

        <Button
          size="sm"
          variant="ghost"
          class="h-7 px-2 text-xs text-muted-foreground hover:text-foreground"
          @click="isCollapsed = !isCollapsed"
        >
          <span class="text-xs">{{ isCollapsed ? t('results.insights.expandPanel') : t('results.insights.collapsePanel') }}</span>
          <component :is="isCollapsed ? ChevronDown : ChevronUp" class="ml-1 h-3.5 w-3.5" />
        </Button>
      </div>
    </div>

    <!-- 可折叠内容区 -->
    <div v-show="!isCollapsed" class="grid gap-5 p-4 sm:p-5 lg:grid-cols-[1.2fr_0.8fr]">
      <!-- 左侧：3个核心价格指标 + 每日趋势曲线图 -->
      <div class="space-y-4">
        <div class="grid gap-2.5 grid-cols-3">
          <article
            v-for="card in summaryCards"
            :key="card.label"
            class="rounded-lg border border-border/70 bg-muted/30 p-3"
          >
            <p class="text-[11px] text-muted-foreground">{{ card.label }}</p>
            <p class="mt-1 text-lg font-bold tabular-nums tracking-tight">{{ card.value }}</p>
            <p class="mt-0.5 text-[10px] text-muted-foreground/80 truncate">{{ card.hint }}</p>
          </article>
        </div>

        <PriceTrendChart :points="insights?.daily_trend || []" />
      </div>

      <!-- 右侧：Kokonut UI 风格行情解读与区间卡片 -->
      <div class="space-y-3">
        <div class="rounded-lg border border-border/70 bg-muted/20 p-4">
          <div class="flex items-center justify-between text-xs text-muted-foreground">
            <span class="flex items-center gap-1 font-medium text-foreground">
              <Sparkles class="h-3.5 w-3.5 text-primary" />
              {{ t('results.insights.trendDigestTitle') }}
            </span>
            <span class="tabular-nums font-semibold text-primary">
              {{ t('results.insights.snapshotCount', { count: insights?.market_summary.sample_count || 0 }) }}
            </span>
          </div>

          <p class="mt-2 text-xs leading-relaxed text-muted-foreground">
            {{ t('results.insights.trendReading') }}
          </p>
        </div>

        <div class="rounded-lg border border-border/70 bg-card p-4 space-y-2.5">
          <div class="flex items-center justify-between text-xs text-muted-foreground">
            <span class="font-medium text-foreground">{{ t('results.insights.priceRangeTitle') }}</span>
            <span class="text-[11px] truncate max-w-[160px]">{{ latestSnapshotText }}</span>
          </div>

          <div class="grid grid-cols-3 gap-2 pt-1 text-xs">
            <div class="rounded-md bg-muted/40 p-2 text-center">
              <p class="text-[10px] text-muted-foreground">{{ t('results.insights.currentMedian') }}</p>
              <p class="mt-0.5 font-semibold tabular-nums">
                {{ insights?.market_summary.median_price ? `¥${insights.market_summary.median_price}` : '—' }}
              </p>
            </div>

            <div class="rounded-md bg-muted/40 p-2 text-center">
              <p class="text-[10px] text-muted-foreground">{{ t('results.insights.historyMin') }}</p>
              <p class="mt-0.5 font-semibold text-emerald-600 dark:text-emerald-400 tabular-nums">
                {{ insights?.history_summary.min_price ? `¥${insights.history_summary.min_price}` : '—' }}
              </p>
            </div>

            <div class="rounded-md bg-muted/40 p-2 text-center">
              <p class="text-[10px] text-muted-foreground">{{ t('results.insights.historyMax') }}</p>
              <p class="mt-0.5 font-semibold text-rose-600 dark:text-rose-400 tabular-nums">
                {{ insights?.history_summary.max_price ? `¥${insights.history_summary.max_price}` : '—' }}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
