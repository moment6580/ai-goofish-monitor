<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import {
  LayoutDashboard,
  ListTodo,
  Users,
  Layers,
  Terminal,
  Settings2,
} from 'lucide-vue-next'
import BrandLogo from '@/components/common/BrandLogo.vue'
import { useWebSocket } from '@/composables/useWebSocket'
import { useI18n } from 'vue-i18n'

const emit = defineEmits<{
  (event: 'navigate'): void
}>()
const route = useRoute()
const { isConnected } = useWebSocket()
const { t } = useI18n()

const mainNavItems = computed(() => [
  { to: '/dashboard', label: t('sidebar.dashboard'), icon: LayoutDashboard },
  { to: '/tasks', label: t('sidebar.tasks'), icon: ListTodo },
  { to: '/results', label: t('sidebar.results'), icon: Layers },
])

const systemNavItems = computed(() => [
  { to: '/accounts', label: t('sidebar.accounts'), icon: Users },
  { to: '/logs', label: t('sidebar.logs'), icon: Terminal },
  { to: '/settings', label: t('sidebar.settings'), icon: Settings2 },
])

function isActiveLink(to: string) {
  return route.path === to || route.path.startsWith(`${to}/`)
}

const connectionLabel = computed(() => (
  isConnected.value ? t('sidebar.backendConnected') : t('sidebar.backendConnecting')
))
</script>

<template>
  <nav class="flex h-full flex-col justify-between" aria-label="Main navigation">
    <div class="space-y-4">
      <!-- 分组 1: 核心监控与捡漏 -->
      <div class="space-y-1">
        <p class="px-3 pb-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/70">
          监控与发现
        </p>

        <RouterLink
          v-for="item in mainNavItems"
          :key="item.to"
          :to="item.to"
          class="relative group flex items-center gap-2.5 rounded-md px-3 py-2 text-xs font-medium transition-colors"
          :class="isActiveLink(item.to)
            ? 'bg-accent text-accent-foreground font-semibold shadow-xs'
            : 'text-muted-foreground hover:bg-accent/60 hover:text-foreground'"
          @click="emit('navigate')"
        >
          <span
            v-if="isActiveLink(item.to)"
            class="absolute left-0 top-1.5 bottom-1.5 w-1 rounded-r-full bg-primary"
          />

          <component
            :is="item.icon"
            class="h-4 w-4 shrink-0 transition-colors"
            :class="isActiveLink(item.to) ? 'text-primary' : 'text-muted-foreground group-hover:text-foreground'"
          />
          <span class="truncate">{{ item.label }}</span>
        </RouterLink>
      </div>

      <!-- 分组 2: 账号与管理 -->
      <div class="space-y-1 pt-1">
        <p class="px-3 pb-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/70">
          控制与配置
        </p>

        <RouterLink
          v-for="item in systemNavItems"
          :key="item.to"
          :to="item.to"
          class="relative group flex items-center gap-2.5 rounded-md px-3 py-2 text-xs font-medium transition-colors"
          :class="isActiveLink(item.to)
            ? 'bg-accent text-accent-foreground font-semibold shadow-xs'
            : 'text-muted-foreground hover:bg-accent/60 hover:text-foreground'"
          @click="emit('navigate')"
        >
          <span
            v-if="isActiveLink(item.to)"
            class="absolute left-0 top-1.5 bottom-1.5 w-1 rounded-r-full bg-primary"
          />

          <component
            :is="item.icon"
            class="h-4 w-4 shrink-0 transition-colors"
            :class="isActiveLink(item.to) ? 'text-primary' : 'text-muted-foreground group-hover:text-foreground'"
          />
          <span class="truncate">{{ item.label }}</span>
        </RouterLink>
      </div>
    </div>

    <!-- 底部状态小卡片 (Kokonut UI 风格) -->
    <div class="pt-4 px-1">
      <div class="rounded-lg border border-border/80 bg-muted/30 p-2.5 space-y-1.5">
        <div class="flex items-center justify-between">
          <span class="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">实时引擎</span>
          <span
            class="inline-flex items-center gap-1 text-[10px] font-medium"
            :class="isConnected ? 'text-emerald-600 dark:text-emerald-400' : 'text-amber-600 dark:text-amber-400'"
          >
            <span class="relative flex h-1.5 w-1.5">
              <span
                v-if="isConnected"
                class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"
              />
              <span
                class="relative inline-flex rounded-full h-1.5 w-1.5"
                :class="isConnected ? 'bg-emerald-500' : 'bg-amber-500'"
              />
            </span>
            {{ connectionLabel }}
          </span>
        </div>

        <div class="flex items-center justify-between text-[11px] text-muted-foreground/80 pt-0.5">
          <span class="flex items-center gap-1.5 font-medium text-foreground">
            <BrandLogo size="xs" />
            AI 捡漏监控
          </span>
          <span class="font-mono text-[10px]">v2.1</span>
        </div>
      </div>
    </div>
  </nav>
</template>
