<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl'
  variant?: 'badge' | 'icon'
  animate?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  size: 'sm',
  variant: 'badge',
  animate: false,
})

const sizeMap = {
  xs: { box: 'h-5 w-5 rounded-[5px]', svg: 'w-3 h-3' },
  sm: { box: 'h-7 w-7 rounded-md', svg: 'w-4 h-4' },
  md: { box: 'h-8 w-8 rounded-lg', svg: 'w-5 h-5' },
  lg: { box: 'h-10 w-10 rounded-xl', svg: 'w-6 h-6' },
  xl: { box: 'h-12 w-12 rounded-2xl', svg: 'w-7 h-7' },
}

const currentSize = computed(() => sizeMap[props.size] || sizeMap.sm)
</script>

<template>
  <div
    v-if="variant === 'badge'"
    class="relative inline-flex shrink-0 items-center justify-center overflow-hidden bg-zinc-900 text-amber-400 border border-zinc-800 shadow-xs dark:bg-zinc-900 dark:border-zinc-700/80 transition-transform duration-300"
    :class="[
      currentSize.box,
      animate ? 'hover:scale-105 group-hover:scale-105' : ''
    ]"
  >
    <!-- Background subtle radial highlight -->
    <div class="pointer-events-none absolute inset-0 bg-radial from-amber-500/10 via-transparent to-transparent opacity-60"></div>

    <!-- AI Fish Vector -->
    <svg
      :class="currentSize.svg"
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      class="relative z-10"
    >
      <defs>
        <linearGradient id="brand-fish-gradient" x1="3" y1="6" x2="28" y2="24" gradientUnits="userSpaceOnUse">
          <stop stop-color="#FBBF24" />
          <stop offset="0.55" stop-color="#F59E0B" />
          <stop offset="1" stop-color="#EA580C" />
        </linearGradient>
      </defs>

      <!-- Dynamic Fish Contour -->
      <path
        d="M27.5 15.5C24.2 9.5 16.8 7.2 8.5 11.2L3 6.8L5.8 15.5L3 24.2L8.5 19.8C16.8 23.8 24.2 21.5 27.5 15.5Z"
        fill="url(#brand-fish-gradient)"
      />

      <!-- Speed fin accent -->
      <path
        d="M13 8.2C15.5 6.2 19 6 21 7.2C19.2 8.8 16.5 9.5 13 8.2Z"
        fill="#FDE68A"
        opacity="0.9"
      />

      <!-- AI Radar / Aperture Eye -->
      <circle cx="19.5" cy="14.5" r="2.8" fill="#18181B" />
      <circle cx="19.5" cy="14.5" r="1.3" fill="#FBBF24" />

      <!-- Crosshair targeting optics -->
      <path
        d="M19.5 10V12M19.5 17V19M15 14.5H17M22 14.5H24"
        stroke="#FFFFFF"
        stroke-width="1.2"
        stroke-linecap="round"
        opacity="0.9"
      />
    </svg>
  </div>

  <!-- Pure SVG icon mode -->
  <svg
    v-else
    :class="currentSize.svg"
    viewBox="0 0 32 32"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
  >
    <defs>
      <linearGradient id="brand-fish-gradient-raw" x1="3" y1="6" x2="28" y2="24" gradientUnits="userSpaceOnUse">
        <stop stop-color="#FBBF24" />
        <stop offset="0.55" stop-color="#F59E0B" />
        <stop offset="1" stop-color="#EA580C" />
      </linearGradient>
    </defs>
    <path
      d="M27.5 15.5C24.2 9.5 16.8 7.2 8.5 11.2L3 6.8L5.8 15.5L3 24.2L8.5 19.8C16.8 23.8 24.2 21.5 27.5 15.5Z"
      fill="url(#brand-fish-gradient-raw)"
    />
    <path
      d="M13 8.2C15.5 6.2 19 6 21 7.2C19.2 8.8 16.5 9.5 13 8.2Z"
      fill="#FDE68A"
      opacity="0.9"
    />
    <circle cx="19.5" cy="14.5" r="2.8" fill="#18181B" />
    <circle cx="19.5" cy="14.5" r="1.3" fill="#FBBF24" />
    <path
      d="M19.5 10V12M19.5 17V19M15 14.5H17M22 14.5H24"
      stroke="#FFFFFF"
      stroke-width="1.2"
      stroke-linecap="round"
      opacity="0.9"
    />
  </svg>
</template>
