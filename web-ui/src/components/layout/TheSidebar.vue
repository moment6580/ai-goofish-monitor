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
import { useWebSocket } from '@/composables/useWebSocket'
import { useI18n } from 'vue-i18n'

const emit = defineEmits<{
  (event: 'navigate'): void
}>()
const route = useRoute()
const { isConnected } = useWebSocket()
const { t } = useI18n()

const navItems = computed(() => [
  { to: '/dashboard', label: t('sidebar.dashboard'), icon: LayoutDashboard },
  { to: '/tasks', label: t('sidebar.tasks'), icon: ListTodo },
  { to: '/accounts', label: t('sidebar.accounts'), icon: Users },
  { to: '/results', label: t('sidebar.results'), icon: Layers },
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
  <nav class="flex h-full flex-col gap-1" aria-label="Main navigation">
    <RouterLink
      v-for="item in navItems"
      :key="item.to"
      :to="item.to"
      class="group flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors"
      :class="isActiveLink(item.to)
        ? 'bg-accent text-accent-foreground'
        : 'text-muted-foreground hover:bg-accent/60 hover:text-foreground'"
      @click="emit('navigate')"
    >
      <component
        :is="item.icon"
        class="h-4 w-4 shrink-0"
        :class="isActiveLink(item.to) ? 'text-foreground' : 'text-muted-foreground group-hover:text-foreground'"
      />
      {{ item.label }}
    </RouterLink>

    <div class="mt-auto px-3 py-2">
      <div class="flex items-center gap-2 rounded-md border border-dashed px-3 py-2.5">
        <span
          class="h-2 w-2 shrink-0 rounded-full"
          :class="isConnected ? 'bg-success' : 'bg-warning'"
          :aria-hidden="true"
        ></span>
        <span class="truncate text-xs text-muted-foreground">{{ connectionLabel }}</span>
      </div>
    </div>
  </nav>
</template>
