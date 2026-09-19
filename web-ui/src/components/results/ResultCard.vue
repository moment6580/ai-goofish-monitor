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
import {
  ExternalLink,
  TrendingDown,
  Info,
  User,
  Clock,
  CheckCircle2,
  XCircle,
  AlertCircle,
  EyeOff,
  Eye,
  ShieldCheck,
  Flame,
  MapPin,
  Sparkles,
} from 'lucide-vue-next'
import { formatDateTime } from '@/i18n'

interface Props {
  item: ResultItem
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'toggle-block', item: ResultItem): void
}>()
const { t } = useI18n()

const info = computed(() => props.item.商品信息 || {})
const seller = computed(() => props.item.卖家信息 || {})
const ai = computed(() => props.item.ai_analysis)
const priceInsight = computed(() => props.item.price_insight)

const isRecommended = computed(() => ai.value?.is_recommended === true)
const recommendationStatus = computed(() => {
  if (ai.value?.is_recommended === true) {
    return {
      label: t('results.card.strongRecommend'),
      bar: 'bg-emerald-500 dark:bg-emerald-400',
      badgeClass: 'bg-emerald-500 text-white border-transparent',
      icon: CheckCircle2,
      text: 'text-emerald-600 dark:text-emerald-400',
    }
  }
  if (ai.value?.is_recommended === false) {
    return {
      label: t('results.card.notRecommended'),
      bar: 'bg-rose-500 dark:bg-rose-400',
      badgeClass: 'bg-rose-500 text-white border-transparent',
      icon: XCircle,
      text: 'text-rose-600 dark:text-rose-400',
    }
  }
  return {
    label: t('results.card.pending'),
    bar: 'bg-amber-500 dark:bg-amber-400',
    badgeClass: 'bg-amber-500 text-white border-transparent',
    icon: AlertCircle,
    text: 'text-amber-600 dark:text-amber-400',
  }
})

const imageUrl = computed(() => info.value.商品图片列表?.[0] || info.value.商品主图链接 || '')
const crawlTime = computed(() => {
  return props.item.爬取时间
    ? formatDateTime(props.item.爬取时间, { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
    : t('common.unknown')
})

const matchScore = computed(() => ai.value?.value_score ?? 0)
const isHidden = computed(() => props.item._effective_hidden === true || props.item._status === 'hidden')
const isRuleHidden = computed(() => props.item._hidden_reason === 'rule')
const canToggleBlock = computed(() => props.item._hidden_reason !== 'rule' && props.item._hidden_reason !== 'expired')
const hiddenLabel = computed(() => {
  if (props.item._hidden_reason === 'rule') return t('results.card.blacklisted')
  if (props.item._hidden_reason === 'expired') return t('results.card.expired')
  return t('results.card.hidden')
})

// 计算捡漏差价（低于市场均价多少）
const dealDiff = computed(() => {
  if (!priceInsight.value?.market_avg_price) return null
  const rawPrice = String(info.value.当前售价 || '').replace(/[^\d.]/g, '')
  const current = parseFloat(rawPrice)
  if (!Number.isFinite(current) || current <= 0) return null
  const diff = priceInsight.value.market_avg_price - current
  if (diff > 5) {
    return Math.round(diff)
  }
  return null
})

// 想要人数
const wantCount = computed(() => info.value['“想要”人数'] || '')
// 发货地区
const location = computed(() => info.value.发货地区 || '')
// 芝麻信用
const zhima = computed(() => seller.value.卖家芝麻信用 || '')
// 注册时长
const regDuration = computed(() => seller.value.卖家注册时长 || '')

const expanded = ref(false)
</script>

<template>
  <Card
    class="group relative flex h-full flex-col overflow-hidden rounded-xl border border-border/80 bg-card shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:border-border hover:shadow-md"
    :class="{ 'opacity-60 grayscale-[40%]': isHidden }"
  >
    <!-- 商品头图区域 (Commerce UI 风格) -->
    <div class="relative aspect-[4/3] w-full overflow-hidden bg-muted/60">
      <div v-if="!imageUrl" class="absolute inset-0 animate-pulse bg-muted"></div>
      <img
        v-else
        :src="imageUrl"
        :alt="info.商品标题"
        class="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
        loading="lazy"
        decoding="async"
        referrerpolicy="no-referrer"
      />

      <!-- 渐变暗角浮层（提升文字可读性） -->
      <div class="pointer-events-none absolute inset-x-0 bottom-0 h-16 bg-gradient-to-t from-black/60 to-transparent"></div>

      <!-- 屏蔽遮罩 -->
      <div v-if="isHidden" class="absolute inset-0 flex items-center justify-center bg-background/80 backdrop-blur-[2px]">
        <Badge variant="outline" class="border-muted-foreground/30 bg-background/90 text-xs font-semibold tracking-wider">
          {{ hiddenLabel }}
        </Badge>
      </div>

      <!-- 左上角电商捡漏与推荐徽章组 -->
      <div class="absolute left-2.5 top-2.5 flex flex-wrap items-center gap-1.5 z-10">
        <Badge
          v-if="isRecommended && !isHidden"
          class="flex items-center gap-1 px-2 py-0.5 text-[11px] font-semibold shadow-sm backdrop-blur-sm"
          :class="recommendationStatus.badgeClass"
        >
          <Sparkles class="h-3 w-3" />
          {{ t('results.card.curated') }}
          <span v-if="matchScore > 0" class="ml-0.5 opacity-90">{{ matchScore }}分</span>
        </Badge>

        <Badge
          v-if="dealDiff"
          class="bg-emerald-600/90 dark:bg-emerald-500/90 text-white border-none px-1.5 py-0.5 text-[10px] font-medium shadow-sm backdrop-blur-sm"
        >
          <TrendingDown class="mr-0.5 h-3 w-3 inline" />
          {{ t('results.card.belowMarketAvg', { amount: dealDiff }) }}
        </Badge>

        <Badge
          v-if="isRuleHidden"
          variant="secondary"
          class="border-none bg-zinc-900/80 text-white px-1.5 py-0.5 text-[10px] backdrop-blur-sm"
        >
          {{ t('results.card.blacklisted') }}
        </Badge>
      </div>

      <!-- 右上角快捷操作悬浮按钮组 -->
      <div class="absolute right-2.5 top-2.5 flex items-center gap-1 z-10">
        <button
          v-if="canToggleBlock"
          type="button"
          @click="emit('toggle-block', props.item)"
          :aria-label="isHidden ? t('results.card.unblock') : t('results.card.block')"
          :title="isHidden ? t('results.card.unblock') : t('results.card.block')"
          class="flex h-7 w-7 items-center justify-center rounded-md bg-black/50 text-white/90 backdrop-blur-md transition-all hover:bg-black/80 hover:text-white"
        >
          <EyeOff v-if="!isHidden" class="h-3.5 w-3.5" />
          <Eye v-else class="h-3.5 w-3.5" />
        </button>

        <a
          :href="info.商品链接"
          target="_blank"
          rel="noopener noreferrer"
          :aria-label="t('results.card.detail')"
          :title="t('results.card.detail')"
          class="flex h-7 w-7 items-center justify-center rounded-md bg-black/50 text-white/90 backdrop-blur-md transition-all hover:bg-black/80 hover:text-white"
        >
          <ExternalLink class="h-3.5 w-3.5" />
        </a>
      </div>

      <!-- 图片底部标签（地理位置 / 想要热度） -->
      <div class="absolute bottom-2 left-2.5 right-2.5 flex items-center justify-between text-[11px] text-white/90 z-10">
        <span v-if="location" class="flex items-center gap-0.5 drop-shadow-sm">
          <MapPin class="h-3 w-3 text-white/80" />
          <span class="truncate max-w-[120px]">{{ location }}</span>
        </span>
        <span v-else></span>

        <span v-if="wantCount" class="flex items-center gap-0.5 font-medium drop-shadow-sm text-amber-300">
          <Flame class="h-3 w-3 fill-amber-300" />
          {{ t('results.card.wantCount', { count: wantCount }) }}
        </span>
      </div>
    </div>

    <!-- 标题与价格区域 (Commerce UI 风格) -->
    <CardHeader class="p-3.5 pb-2 space-y-1.5">
      <CardTitle class="line-clamp-2 min-h-[2.5rem] text-[13px] font-medium leading-snug">
        <a
          :href="info.商品链接"
          target="_blank"
          rel="noopener noreferrer"
          class="transition-colors hover:text-primary"
        >
          {{ info.商品标题 }}
        </a>
      </CardTitle>

      <!-- 价格栏 -->
      <div class="flex items-baseline justify-between gap-2 pt-0.5">
        <div class="flex items-baseline gap-1.5">
          <span class="text-xl font-bold tracking-tight text-rose-600 dark:text-rose-400 tabular-nums">
            {{ info.当前售价 }}
          </span>
          <span v-if="info['商品原价']" class="text-xs text-muted-foreground line-through tabular-nums">
            {{ info['商品原价'] }}
          </span>
        </div>

        <span
          v-if="priceInsight?.market_avg_price"
          class="text-[11px] text-muted-foreground/80 tabular-nums"
          :title="t('results.card.marketAvg', { price: priceInsight.market_avg_price })"
        >
          {{ t('results.card.marketAvgShort', { price: priceInsight.market_avg_price }) }}
        </span>
      </div>
    </CardHeader>

    <!-- 智能分析与行情对比 (Cult UI 风格) -->
    <CardContent class="flex-grow p-3.5 pt-0 space-y-2.5">
      <!-- AI 诊断盒 -->
      <div class="rounded-lg border border-border/70 bg-muted/30 p-2.5 text-xs transition-colors">
        <div class="flex items-center justify-between mb-1.5">
          <div class="flex items-center gap-1.5 font-medium" :class="recommendationStatus.text">
            <component :is="recommendationStatus.icon" class="h-3.5 w-3.5 shrink-0" />
            <span>{{ recommendationStatus.label }}</span>
          </div>

          <div class="flex items-center gap-1 text-[11px] text-muted-foreground">
            <span>{{ t('results.card.matchScore') }}</span>
            <span class="font-bold tabular-nums" :class="recommendationStatus.text">{{ matchScore }}%</span>
          </div>
        </div>

        <!-- 极简匹配度进度条 -->
        <div class="mb-2 h-1 w-full overflow-hidden rounded-full bg-border/80">
          <div
            class="h-full rounded-full transition-all duration-500 ease-out"
            :class="recommendationStatus.bar"
            :style="{ width: `${matchScore}%` }"
          ></div>
        </div>

        <!-- 理由摘要 -->
        <p class="leading-relaxed text-muted-foreground" :class="{ 'line-clamp-2': !expanded }">
          {{ ai?.reason || t('results.card.analyzing') }}
        </p>

        <!-- 展开/收起按钮 -->
        <button
          v-if="ai?.reason && ai.reason.length > 45"
          type="button"
          @click="expanded = !expanded"
          class="mt-1 inline-flex items-center gap-0.5 text-[10px] font-medium text-primary hover:underline"
        >
          {{ expanded ? t('results.card.collapse') : t('results.card.expand') }}
          <Info class="h-3 w-3" />
        </button>
      </div>

      <!-- 卖家信用微标签 -->
      <div v-if="zhima || regDuration" class="flex flex-wrap items-center gap-1.5 text-[11px] text-muted-foreground">
        <span
          v-if="zhima"
          class="inline-flex items-center gap-1 rounded bg-blue-500/10 px-1.5 py-0.5 font-medium text-blue-600 dark:text-blue-400"
        >
          <ShieldCheck class="h-3 w-3" />
          {{ zhima }}
        </span>

        <span
          v-if="regDuration"
          class="rounded bg-muted px-1.5 py-0.5"
        >
          {{ regDuration }}
        </span>
      </div>
    </CardContent>

    <!-- 底部信息与动作栏 (Commerce UI 风格) -->
    <CardFooter class="flex items-center justify-between border-t border-border/60 bg-muted/20 px-3.5 py-2 text-[11px] text-muted-foreground">
      <div class="flex items-center gap-2.5 truncate max-w-[170px]">
        <div class="flex items-center gap-1 truncate">
          <User class="h-3 w-3 shrink-0 opacity-70" />
          <span class="truncate">{{ seller.卖家昵称 || info.卖家昵称 || t('results.card.anonymous') }}</span>
        </div>
        <span class="text-border">·</span>
        <div class="flex items-center gap-1 shrink-0">
          <Clock class="h-3 w-3 opacity-70" />
          <span>{{ crawlTime }}</span>
        </div>
      </div>

      <a
        :href="info.商品链接"
        target="_blank"
        rel="noopener noreferrer"
        class="inline-flex items-center gap-1 text-[11px] font-medium text-primary hover:underline"
      >
        <span>{{ t('results.card.detail') }}</span>
        <ExternalLink class="h-3 w-3" />
      </a>
    </CardFooter>
  </Card>
</template>
