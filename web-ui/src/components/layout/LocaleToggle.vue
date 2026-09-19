<script setup lang="ts">
import { useLocale } from '@/i18n'
import { useI18n } from 'vue-i18n'

const { locale, toggleLocale } = useLocale()
const { t } = useI18n()

const localeOptions = [
  { value: 'zh-CN', label: '中文', shortLabel: '中' },
  { value: 'en-US', label: 'English', shortLabel: 'EN' },
] as const
</script>

<template>
  <div
    class="inline-flex items-center gap-0.5 rounded-md border bg-muted/50 p-0.5"
    :aria-label="t('locale.switchLabel')"
    role="group"
  >
    <button
      v-for="option in localeOptions"
      :key="option.value"
      type="button"
      class="rounded-[calc(var(--radius)-2px)] px-2 py-1 text-xs font-medium transition-colors"
      :class="locale === option.value
        ? 'bg-background text-foreground shadow-sm'
        : 'text-muted-foreground hover:text-foreground'"
      @click="toggleLocale(option.value)"
    >
      <span class="sm:hidden">{{ option.shortLabel }}</span>
      <span class="hidden sm:inline">{{ option.label }}</span>
    </button>
  </div>
</template>
