<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Button } from '@/components/ui/button'
import DashboardTaskSearch from '@/components/layout/DashboardTaskSearch.vue'
import LocaleToggle from '@/components/layout/LocaleToggle.vue'
import {
  Zap,
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
import { useI18n } from 'vue-i18n'

const router = useRouter()
const route = useRoute()
const { toggleMobileNav } = useMobileNav()
const { isDark, toggleTheme } = useTheme()
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
    <!-- Brand Logo -->
    <RouterLink
      to="/dashboard"
      class="flex items-center gap-2.5 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      :aria-label="t('header.goHome')"
    >
      <div class="flex h-7 w-7 items-center justify-center rounded-md bg-primary text-primary-foreground">
        <Zap class="h-4 w-4 fill-current" />
      </div>
      <h1 class="hidden text-sm font-semibold tracking-tight sm:block">
        AI Xianyu Hunter
      </h1>
    </RouterLink>

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
          class="h-9 w-full rounded-md border border-input bg-transparent pl-9 pr-3 text-sm text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring/30"
        />
      </div>
    </div>

    <!-- Actions -->
    <div class="flex items-center gap-1.5">
      <Button
        variant="ghost"
        size="icon"
        class="h-9 w-9"
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
        class="h-9 w-9"
        :aria-label="t('header.openNotifications')"
        @click="goNotifications"
      >
        <Bell class="h-4 w-4" />
      </Button>
      <Button
        variant="ghost"
        size="icon"
        class="hidden h-9 w-9 sm:inline-flex"
        :aria-label="t('header.openPrompts')"
        @click="goPrompts"
      >
        <HelpCircle class="h-4 w-4" />
      </Button>

      <Button
        variant="ghost"
        class="hidden gap-2 px-2 sm:flex"
        :aria-label="t('header.openAccounts')"
        @click="goAccounts"
      >
        <div class="flex h-7 w-7 items-center justify-center overflow-hidden rounded-full border bg-muted">
          <UserCircle class="h-5 w-5 text-muted-foreground" />
        </div>
        <span class="hidden text-sm font-medium lg:block">{{ t('header.accountManagement') }}</span>
      </Button>

      <Button
        variant="ghost"
        size="icon"
        class="h-9 w-9 md:hidden"
        :aria-label="t('header.openNavigation')"
        @click="toggleMobileNav"
      >
        <Menu class="h-5 w-5" />
      </Button>
    </div>
  </header>
</template>
