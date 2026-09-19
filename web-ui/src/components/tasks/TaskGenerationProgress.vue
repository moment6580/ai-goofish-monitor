<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Badge } from '@/components/ui/badge'
import type { TaskGenerationJob, TaskGenerationStep } from '@/types/task.d.ts'

const props = defineProps<{
  job: TaskGenerationJob
}>()
const { t } = useI18n()

const statusMeta = computed(() => {
  if (props.job.status === 'completed') {
    return { label: t('tasks.generation.status.completed'), variant: 'default' as const }
  }
  if (props.job.status === 'failed') {
    return { label: t('tasks.generation.status.failed'), variant: 'destructive' as const }
  }
  if (props.job.status === 'running') {
    return { label: t('tasks.generation.status.running'), variant: 'secondary' as const }
  }
  return { label: t('tasks.generation.status.queued'), variant: 'outline' as const }
})

function resolveStepDotClass(step: TaskGenerationStep) {
  if (step.status === 'completed') return 'border-success bg-success'
  if (step.status === 'running') return 'border-warning bg-warning shadow-[0_0_0_4px_hsl(var(--warning)/0.18)]'
  if (step.status === 'failed') return 'border-red-500 bg-red-500'
  return 'border-input bg-background'
}

function resolveStepTextClass(step: TaskGenerationStep) {
  if (step.status === 'completed') return 'text-foreground'
  if (step.status === 'running') return 'text-foreground'
  if (step.status === 'failed') return 'text-destructive'
  return 'text-muted-foreground'
}
</script>

<template>
  <section class="rounded-lg border bg-muted/30 p-4">
    <div class="flex items-start justify-between gap-4">
      <div class="space-y-1">
        <p class="text-sm font-medium">
          {{ job.task_name }}
        </p>
        <p class="text-sm text-muted-foreground">
          {{ job.message }}
        </p>
      </div>
      <Badge :variant="statusMeta.variant">
        {{ statusMeta.label }}
      </Badge>
    </div>

    <div class="mt-4 grid gap-3">
      <div
        v-for="step in job.steps"
        :key="step.key"
        class="flex items-start gap-3 rounded-xl border border-white/70 bg-white px-3 py-2"
      >
        <span
          class="mt-1 h-3 w-3 shrink-0 rounded-full border-2 transition-colors"
          :class="resolveStepDotClass(step)"
        />
        <div class="min-w-0 space-y-1">
          <p class="text-sm font-medium" :class="resolveStepTextClass(step)">
            {{ step.label }}
          </p>
          <p
            v-if="step.message"
            class="text-xs"
            :class="step.status === 'failed' ? 'text-destructive' : 'text-muted-foreground'"
          >
            {{ step.message }}
          </p>
        </div>
      </div>
    </div>

    <p
      v-if="job.error"
      class="mt-4 rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive"
    >
      {{ job.error }}
    </p>
  </section>
</template>
