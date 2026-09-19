<script setup lang="ts">
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { ResultItem } from '@/types/result.d.ts'
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import Badge from '@/components/ui/badge/Badge.vue'
import { ExternalLink, TrendingUp, TrendingDown, Info, User, Clock, CheckCircle2, XCircle, AlertCircle, EyeOff, Eye } from 'lucide-vue-next'
import { formatDateTime } from '@/i18n'

interface Props {
  item: ResultItem
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'toggle-block', item: ResultItem): void
}>()
const { t } = useI18n()

const info = props.item.商品信息
const seller = props.item.卖家信息
const ai = props.item.ai_analysis
const priceInsight = props.item.price_insight

const isRecommended = ai?.is_recommended === true
const recommendationStatus = computed(() => {
  if (ai?.is_recommended === true) return { label: t('results.card.strongRecommend'), bar: 'bg-success', icon: CheckCircle2, text: 'text-success' }
  if (ai?.is_recommended === false) return { label: t('results.card.notRecommended'), bar: 'bg-destructive', icon: XCircle, text: 'text-destructive' }
  return { label: t('results.card.pending'), bar: 'bg-warning', icon: AlertCircle, text: 'text-warning' }
})

const imageUrl = info.商品图片列表?.[0] || info.商品主图链接 || ''
const crawlTime = props.item.爬取时间
  ? formatDateTime(props.item.爬取时间, { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
  : t('common.unknown')
const matchScore = ai?.value_score ?? 0
const isHidden = computed(() => props.item._effective_hidden === true || props.item._status === 'hidden')
const isRuleHidden = computed(() => props.item._hidden_reason === 'rule')
const canToggleBlock = computed(() => props.item._hidden_reason !== 'rule' && props.item._hidden_reason !== 'expired')
const hiddenLabel = computed(() => {
  if (props.item._hidden_reason === 'rule') return t('results.card.blacklisted')
  if (props.item._hidden_reason === 'expired') return t('results.card.expired')
  return t('results.card.hidden')
})

const expanded = ref(false)
</script>

<template>
  <Card class="group flex h-full flex-col overflow-hidden p-0 shadow-card transition-shadow hover:shadow-card-hover" :class="{ 'opacity-60': isHidden }">
    <!-- 商品图 -->
    <div class="relative aspect-[4/3] overflow-hidden bg-muted">
      <div v-if="!imageUrl" class="absolute inset-0 animate-pulse bg-muted"></div>
      <img
        v-else
        :src="imageUrl"
        :alt="info.商品标题"
        class="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
        loading="lazy"
      />
      <div v-if="isHidden" class="absolute inset-0 flex items-center justify-center bg-black/40">
        <span class="text-xs font-medium uppercase tracking-wider text-white/90">{{ hiddenLabel }}</span>
      </div>
      <div class="absolute left-3 top-3 flex gap-2">
        <Badge v-if="isRecommended && !isHidden" class="border-none bg-success text-success-foreground hover:bg-success">
          {{ t('results.card.curated') }}
        </Badge>
        <Badge v-if="isRuleHidden" class="border-none bg-foreground/80 text-background hover:bg-foreground/80">
          {{ t('results.card.blacklisted') }}
        </Badge>
      </div>
      <div class="absolute right-3 top-3 flex gap-1.5">
        <button
          v-if="canToggleBlock"
          type="button"
          @click="emit('toggle-block', props.item)"
          :aria-label="isHidden ? t('results.card.unblock') : t('results.card.block')"
          class="flex rounded-md bg-black/40 p-1.5 text-white opacity-100 backdrop-blur-sm transition-opacity hover:bg-black/60 sm:opacity-0 sm:group-hover:opacity-100 sm:focus-visible:opacity-100"
        >
          <EyeOff v-if="!isHidden" class="h-3.5 w-3.5" />
          <Eye v-else class="h-3.5 w-3.5" />
        </button>
        <a
          :href="info.商品链接"
          target="_blank"
          rel="noopener noreferrer"
          :aria-label="t('results.card.detail')"
          class="flex rounded-md bg-black/40 p-1.5 text-white opacity-100 backdrop-blur-sm transition-opacity hover:bg-black/60 sm:opacity-0 sm:group-hover:opacity-100 sm:focus-visible:opacity-100"
        >
          <ExternalLink class="h-3.5 w-3.5" />
        </a>
      </div>
    </div>

    <CardHeader class="space-y-1.5 p-4 pb-2">
      <CardTitle class="line-clamp-2 h-10 text-sm font-medium leading-snug">
        <a :href="info.商品链接" target="_blank" rel="noopener noreferrer" class="transition-colors hover:text-primary">
          {{ info.商品标题 }}
        </a>
      </CardTitle>
      <div class="flex items-baseline gap-1.5">
        <span class="text-xl font-semibold tabular-nums tracking-tight">{{ info.当前售价 }}</span>
        <span v-if="info['商品原价']" class="mb-0.5 text-xs text-muted-foreground line-through">{{ info['商品原价'] }}</span>
      </div>
    </CardHeader>

    <CardContent class="flex-grow p-4 pt-0">
      <!-- AI 分析 -->
      <div class="rounded-md border bg-muted/40 p-3">
        <div class="mb-2 flex items-center justify-between">
          <div class="flex items-center gap-1.5">
            <component :is="recommendationStatus.icon" class="h-3.5 w-3.5" :class="recommendationStatus.text" />
            <span class="text-xs font-medium" :class="recommendationStatus.text">{{ recommendationStatus.label }}</span>
          </div>
          <div class="flex items-center gap-1">
            <span class="text-[10px] text-muted-foreground">AI Match</span>
            <span class="text-xs font-semibold tabular-nums" :class="recommendationStatus.text">{{ matchScore }}%</span>
          </div>
        </div>

        <div class="mb-2.5 h-1 w-full overflow-hidden rounded-full bg-border">
          <div
            class="h-full rounded-full transition-all duration-500 ease-out"
            :class="recommendationStatus.bar"
            :style="{ width: `${matchScore}%` }"
          ></div>
        </div>

        <p class="text-xs leading-relaxed text-muted-foreground" :class="{ 'line-clamp-2': !expanded }">
          {{ ai?.reason || t('results.card.analyzing') }}
        </p>

        <button
          type="button"
          v-if="ai?.reason && ai.reason.length > 50"
          @click="expanded = !expanded"
          class="mt-1 flex items-center gap-1 text-[10px] font-medium text-muted-foreground transition-colors hover:text-foreground"
        >
          {{ expanded ? t('results.card.collapse') : t('results.card.expand') }}
          <Info class="h-3 w-3" />
        </button>
      </div>

      <!-- 价格参考 -->
      <div v-if="priceInsight?.observation_count" class="mt-3 grid grid-cols-2 gap-2">
        <div class="rounded-md border bg-background p-2.5">
          <div class="mb-1 flex items-center gap-1 text-[10px] text-muted-foreground">
            <TrendingUp class="h-3 w-3" /> {{ t('results.card.marketAvg') }}
          </div>
          <div class="text-sm font-medium tabular-nums">
            {{ priceInsight.market_avg_price ? `¥${priceInsight.market_avg_price}` : '—' }}
          </div>
        </div>
        <div class="rounded-md border bg-background p-2.5">
          <div class="mb-1 flex items-center gap-1 text-[10px] text-muted-foreground">
            <TrendingDown class="h-3 w-3" /> {{ t('results.card.historicalLow') }}
          </div>
          <div class="text-sm font-medium tabular-nums">
            {{ priceInsight.min_price ? `¥${priceInsight.min_price}` : '—' }}
          </div>
        </div>
      </div>
    </CardContent>

    <CardFooter class="flex items-center justify-between border-t bg-muted/30 px-4 py-2.5 text-[11px] text-muted-foreground">
      <div class="flex items-center gap-3">
        <div class="flex items-center gap-1">
          <User class="h-3 w-3" />
          <span class="max-w-[70px] truncate">{{ seller.卖家昵称 || info.卖家昵称 || t('results.card.anonymous') }}</span>
        </div>
        <div class="flex items-center gap-1">
          <Clock class="h-3 w-3" />
          <span>{{ crawlTime }}</span>
        </div>
      </div>
      <a :href="info.商品链接" target="_blank" rel="noopener noreferrer" class="flex items-center gap-1 font-medium text-primary/80 transition-colors hover:text-primary">
        {{ t('results.card.detail') }} <ExternalLink class="h-3 w-3" />
      </a>
    </CardFooter>
  </Card>
</template>
