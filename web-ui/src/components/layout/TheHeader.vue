<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Button } from '@/components/ui/button'
import DashboardTaskSearch from '@/components/layout/DashboardTaskSearch.vue'
import LocaleToggle from '@/components/layout/LocaleToggle.vue'
import Badge from '@/components/ui/badge/Badge.vue'
import {
  Bell,
  Search,
  UserCircle,
  HelpCircle,
  Menu,
  Sun,
  Moon,
} from 'lucide-vue-next'
import { useMobileNav } from '@/composables/useMobileNav'
import { useTheme } from '@/composables/useTheme'
import { useWebSocket } from '@/composables/useWebSocket'
import { useI18n } from 'vue-i18n'

const router = useRouter()
const route = useRoute()
const { toggleMobileNav } = useMobileNav()
const { isDark, toggleTheme } = useTheme()
const { isConnected } = useWebSocket()
const inactiveSearchValue = ref('')
const { t } = useI18n()

const isDashboard = computed(() => route.name === 'Dashboard')

function goAccounts() {
  router.push('/accounts')
}

function goNotifications() {
  router.push({ name: 'Settings', query: { tab: 'notifications' } })
}

function goPrompts() {
  router.push({ name: 'Settings', query: { tab: 'prompts' } })
}
</script>

<template>
  <header class="flex h-14 items-center justify-between gap-4 px-4 md:px-6">
    <!-- Brand Text -->
    <div class="flex items-center gap-3">
      <RouterLink
        to="/dashboard"
        class="flex items-center gap-2 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        :aria-label="t('header.goHome')"
      >
        <h1 class="text-sm font-semibold tracking-tight">
          Xianyu Hunter
        </h1>
        <Badge variant="outline" class="hidden sm:inline-flex text-[10px] px-1.5 py-0 h-4 font-normal text-muted-foreground">
          Monitor
        </Badge>
      </RouterLink>

      <!-- 实时连接状态小药丸 (Kokonut UI 风格) -->
      <div
        class="hidden lg:inline-flex items-center gap-1.5 rounded-full border border-border/80 bg-muted/40 px-2 py-0.5 text-[11px] text-muted-foreground"
      >
        <span class="relative flex h-2 w-2">
          <span
            v-if="isConnected"
            class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"
          />
          <span
            class="relative inline-flex rounded-full h-2 w-2"
            :class="isConnected ? 'bg-emerald-500' : 'bg-amber-500'"
          />
        </span>
        <span>{{ isConnected ? '实时就绪' : '连接中' }}</span>
      </div>
    </div>

    <!-- Search -->
    <div class="hidden max-w-md flex-grow md:flex md:mx-6">
      <DashboardTaskSearch v-if="isDashboard" />
      <div v-else class="relative w-full">
        <Search class="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <input
          type="text"
          v-model="inactiveSearchValue"
          readonly
          aria-disabled="true"
          :placeholder="t('header.searchUnavailable')"
          class="h-9 w-full rounded-md border border-input bg-transparent pl-9 pr-3 text-xs text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring/30"
        />
      </div>
    </div>

    <!-- Actions -->
    <div class="flex items-center gap-1.5">
      <Button
        variant="ghost"
        size="icon"
        class="h-8 w-8 text-muted-foreground hover:text-foreground"
        :aria-label="t('header.toggleTheme')"
        @click="toggleTheme"
      >
        <Sun v-if="isDark" class="h-4 w-4" />
        <Moon v-else class="h-4 w-4" />
      </Button>

      <LocaleToggle />

      <Button
        variant="ghost"
        size="icon"
        class="h-8 w-8 text-muted-foreground hover:text-foreground"
        :aria-label="t('header.openNotifications')"
        @click="goNotifications"
      >
        <Bell class="h-4 w-4" />
      </Button>

      <Button
        variant="ghost"
        size="icon"
        class="hidden h-8 w-8 text-muted-foreground hover:text-foreground sm:inline-flex"
        :aria-label="t('header.openPrompts')"
        @click="goPrompts"
      >
        <HelpCircle class="h-4 w-4" />
      </Button>

      <Button
        variant="ghost"
        size="sm"
        class="hidden gap-1.5 px-2 text-xs font-medium text-muted-foreground hover:text-foreground sm:flex"
        :aria-label="t('header.openAccounts')"
        @click="goAccounts"
      >
        <div class="flex h-6 w-6 items-center justify-center overflow-hidden rounded-full border bg-muted">
          <UserCircle class="h-4 w-4 text-muted-foreground" />
        </div>
        <span class="hidden lg:block">{{ t('header.accountManagement') }}</span>
      </Button>

      <Button
        variant="ghost"
        size="icon"
        class="h-8 w-8 text-muted-foreground md:hidden"
        :aria-label="t('header.openNavigation')"
        @click="toggleMobileNav"
      >
        <Menu class="h-4 w-4" />
      </Button>
    </div>
  </header>
</template>
