<script setup lang="ts">
import type { ResultItem } from '@/types/result.d.ts'
import { useI18n } from 'vue-i18n'
import ResultCard from './ResultCard.vue'

interface Props {
  results: ResultItem[]
  isLoading: boolean
}

defineProps<Props>()
const { t } = useI18n()

const emit = defineEmits<{
  (e: 'toggle-block', item: ResultItem): void
}>()
const skeletonItems = Array.from({ length: 8 }, (_, index) => index)
</script>

<template>
  <div :aria-busy="isLoading">
    <div
      v-if="isLoading"
      class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
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
    <div v-else class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      <ResultCard v-for="item in results" :key="item.商品信息.商品ID" :item="item" @toggle-block="emit('toggle-block', $event)" />
    </div>
  </div>
</template>
