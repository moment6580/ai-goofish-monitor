<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import TheHeader from '@/components/layout/TheHeader.vue'
import TheSidebar from '@/components/layout/TheSidebar.vue'
import { useMobileNav } from '@/composables/useMobileNav'

const { isMobileNavOpen, closeMobileNav } = useMobileNav()
const { t } = useI18n()
</script>

<template>
  <div class="relative min-h-screen w-full flex flex-col bg-background selection:bg-primary/15">
    <a
      href="#main-content"
      class="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-[120] focus:rounded-lg focus:bg-primary focus:px-4 focus:py-2 focus:text-sm focus:font-semibold focus:text-primary-foreground"
    >
      {{ t('common.skipToContent') }}
    </a>

    <!-- Header -->
    <TheHeader class="sticky top-0 z-50 w-full border-b bg-background/95 supports-[backdrop-filter]:bg-background/80 backdrop-blur" />

    <transition name="mobile-nav">
      <div v-if="isMobileNavOpen" class="fixed inset-0 z-[90] md:hidden">
        <button
          type="button"
          class="absolute inset-0 bg-black/40"
          :aria-label="t('common.close')"
          @click="closeMobileNav"
        />
        <aside class="relative h-full w-72 border-r bg-background p-4 shadow-lg">
          <TheSidebar class="pt-16" @navigate="closeMobileNav" />
        </aside>
      </div>
    </transition>

    <div class="flex flex-grow">
      <!-- Sidebar -->
      <aside class="hidden md:block w-56 flex-shrink-0 border-r bg-background">
        <TheSidebar class="sticky top-14 h-[calc(100vh-3.5rem)] overflow-y-auto p-3" />
      </aside>

      <!-- Main Content Area -->
      <main id="main-content" tabindex="-1" class="flex-grow overflow-x-hidden p-4 focus:outline-none md:p-6">
        <div class="mx-auto max-w-6xl">
          <RouterView />
        </div>
      </main>
    </div>
  </div>
</template>

<style scoped>
.mobile-nav-enter-active,
.mobile-nav-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.mobile-nav-enter-from,
.mobile-nav-leave-to {
  opacity: 0;
  transform: translateX(-12px);
}

@media (prefers-reduced-motion: reduce) {
  .page-enter-active,
  .page-leave-active,
  .mobile-nav-enter-active,
  .mobile-nav-leave-active {
    transition: none;
  }

  .page-enter-from,
  .page-leave-to,
  .mobile-nav-enter-from,
  .mobile-nav-leave-to {
    opacity: 1;
    transform: none;
  }
}
</style>
