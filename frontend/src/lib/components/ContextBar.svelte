<script lang="ts">
  import { link } from 'svelte-spa-router';
  import { context } from '../data/zeteo-data';
  import BusinessPicker from './BusinessPicker.svelte';
  import ChipSelect from './ChipSelect.svelte';

  const periodOptions = ['FY26 Q1', 'FY26 Q2', 'FY26 Q3', 'FY26 Q4'];
  const comparisonOptions = ['vs Budget', 'vs Prior Year', 'vs Forecast'];

  interface Crumb {
    id: string;
    name: string;
    href: string;
  }

  let {
    ancestors = [],
    currentLabel = '',
    refreshedAt = '',
  }: { ancestors?: Crumb[]; currentLabel?: string; refreshedAt?: string } = $props();
</script>

<div class="flex items-center gap-2.5 pb-4 text-xs flex-wrap border-b border-gray-200 dark:border-gray-700">
  <BusinessPicker />
  <ChipSelect id="period-select" prefix="Period: " options={periodOptions} selected={context.period} />
  <ChipSelect id="comparison-select" options={comparisonOptions} selected={context.comparison} />

  {#if ancestors.length || currentLabel}
    <span class="ml-2 text-gray-700 dark:text-gray-300 text-sm">
      {#each ancestors as crumb, i (crumb.id)}
        <a
          href={crumb.href}
          use:link
          class="text-gray-500 dark:text-gray-400 no-underline hover:text-indigo-600 dark:hover:text-indigo-400 hover:underline"
          >{crumb.name}</a
        >
        {#if i < ancestors.length - 1 || currentLabel}<span class="text-gray-500 dark:text-gray-400 mx-1">›</span>{/if}
      {/each}
      {#if currentLabel}<strong>{currentLabel}</strong>{/if}
    </span>
  {/if}

  {#if refreshedAt}
    <span class="ml-auto text-gray-500 dark:text-gray-400 whitespace-nowrap">{refreshedAt}</span>
  {/if}
</div>
