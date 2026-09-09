<script lang="ts">
  import type { SensitivityProgress } from '../data/types';

  // First progress-bar UI in the app — every other analysis (Trend/Variance)
  // shows a spinner only, since none of them stream (see docs/adr/0043).
  let { progress }: { progress: SensitivityProgress | null } = $props();

  const pct = $derived(progress && progress.total > 0 ? Math.min(100, (progress.completed / progress.total) * 100) : 0);
</script>

<div class="flex flex-col items-center justify-center gap-2 py-6">
  <div class="w-64 rounded-full bg-gray-200 dark:bg-gray-700">
    <div class="h-2 rounded-full bg-indigo-600 transition-all dark:bg-indigo-400" style="width: {pct}%"></div>
  </div>
  <div class="text-sm text-gray-500 dark:text-gray-400">
    {#if progress && progress.total > 0}
      Testing driver {progress.completed} of {progress.total}…
    {:else}
      Starting sensitivity run…
    {/if}
  </div>
</div>
