<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { ResultItem } from '@/types/result.d.ts'
import { useI18n } from 'vue-i18n'
import { Button } from '@/components/ui/button'
import { ChevronDown } from 'lucide-vue-next'
import ResultCard from './ResultCard.vue'

interface Props {
  results: ResultItem[]
  isLoading: boolean
}

const props = defineProps<Props>()
const { t } = useI18n()

const emit = defineEmits<{
  (e: 'toggle-block', item: ResultItem): void
}>()
const skeletonItems = Array.from({ length: 8 }, (_, index) => index)

// 增量渲染：首屏渲染 60 条，滚动到底部或点击加载更多
const PAGE_SIZE = 60
const visibleCount = ref(PAGE_SIZE)

const visibleResults = computed(() => props.results.slice(0, visibleCount.value))
const hasMore = computed(() => visibleCount.value < props.results.length)

// 结果集变化（切换筛选/文件）时重置分页
watch(
  () => props.results,
  () => {
    visibleCount.value = PAGE_SIZE
  },
)

function loadMore() {
  visibleCount.value += PAGE_SIZE
}
</script>

<template>
  <div :aria-busy="isLoading">
    <div
      v-if="isLoading"
      class="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
      aria-live="polite"
    >
      <div
        v-for="item in skeletonItems"
        :key="item"
        class="overflow-hidden rounded-lg border bg-card"
      >
        <div class="aspect-[4/3] animate-pulse bg-muted"></div>
        <div class="space-y-3 p-4">
          <div class="h-5 w-4/5 animate-pulse rounded bg-muted"></div>
          <div class="h-7 w-1/3 animate-pulse rounded bg-muted"></div>
          <div class="rounded-md border bg-muted/40 p-3">
            <div class="h-4 w-1/2 animate-pulse rounded bg-muted"></div>
            <div class="mt-3 h-2 w-full animate-pulse rounded bg-muted"></div>
            <div class="mt-3 h-4 w-full animate-pulse rounded bg-muted"></div>
            <div class="mt-2 h-4 w-3/4 animate-pulse rounded bg-muted"></div>
          </div>
        </div>
      </div>
    </div>
    <div v-else-if="results.length === 0" class="rounded-lg border border-dashed py-16 text-center text-sm text-muted-foreground">
      {{ t('results.grid.empty') }}
    </div>
    <template v-else>
      <div class="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        <ResultCard
          v-for="item in visibleResults"
          :key="item.商品信息.商品ID"
          :item="item"
          @toggle-block="emit('toggle-block', $event)"
        />
      </div>

      <div v-if="hasMore" class="mt-4 flex flex-col items-center gap-1.5">
        <Button variant="outline" size="sm" class="text-xs" @click="loadMore">
          <ChevronDown class="h-3.5 w-3.5" />
          {{ t('results.grid.loadMore', { shown: visibleCount, total: results.length }) }}
        </Button>
      </div>
    </template>
  </div>
</template>
