<script lang="ts">
  import { link } from 'svelte-spa-router';
  import type { KpiCard } from '../data/types';
  import Sparkline from './Sparkline.svelte';

  let { kpi }: { kpi: KpiCard } = $props();

  const deltaColorClass = $derived(
    kpi.direction === 'adverse'
      ? 'text-red-600 dark:text-red-400'
      : kpi.direction === 'favourable'
        ? 'text-green-600 dark:text-green-400'
        : 'text-gray-500 dark:text-gray-400'
  );

  const cardBorderClass = $derived(
    kpi.highlighted ? 'border-red-600 dark:border-red-400' : 'border-gray-200 dark:border-gray-700'
  );
</script>

{#snippet body()}
  <div class="text-xs text-gray-500 dark:text-gray-400">{kpi.label}</div>
  <div class="font-black text-lg text-gray-900 dark:text-gray-50">{kpi.value}</div>
  {#if kpi.delta}
    <div class="text-xs font-semibold {deltaColorClass}">{kpi.delta}</div>
  {/if}
  {#if kpi.trend?.length}
    <div class="mt-2"><Sparkline points={kpi.trend} width={70} height={20} /></div>
  {/if}
{/snippet}

{#if kpi.nodeId}
  <a
    class="border-[1.5px] rounded-lg p-2.5 bg-white dark:bg-gray-800 no-underline block cursor-pointer transition-opacity duration-150 hover:opacity-[0.85] {cardBorderClass}"
    href="/vdt/{kpi.nodeId}"
    use:link
  >
    {@render body()}
  </a>
{:else}
  <div class="border-[1.5px] rounded-lg p-2.5 bg-white dark:bg-gray-800 no-underline block {cardBorderClass}">
    {@render body()}
  </div>
{/if}
