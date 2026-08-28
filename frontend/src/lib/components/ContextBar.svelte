<script lang="ts">
  import { link } from 'svelte-spa-router';
  import { context } from '../data/zeteo-data';
  import BusinessPicker from './BusinessPicker.svelte';

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

<div class="bg-gray-100 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
  <div class="shell flex items-center gap-2.5 py-2 text-xs flex-wrap">
    <BusinessPicker />
    <span
      class="border border-gray-200 dark:border-gray-700 rounded-full py-0.5 px-2.5 text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 whitespace-nowrap"
      >Period: {context.period} ▾</span
    >
    <span
      class="border border-gray-200 dark:border-gray-700 rounded-full py-0.5 px-2.5 text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 whitespace-nowrap"
      >{context.comparison} ▾</span
    >

    {#if ancestors.length || currentLabel}
      <span class="ml-2 text-gray-700 dark:text-gray-300 text-sm">
        {#each ancestors as crumb, i (crumb.id)}
          <a
            href={crumb.href}
            use:link
            class="text-gray-500 dark:text-gray-400 no-underline hover:text-indigo-600 dark:hover:text-indigo-400 hover:underline"
            >{crumb.name}</a
          >
          <span class="text-gray-500 dark:text-gray-400 mx-1">›</span>
        {/each}
        {#if currentLabel}<strong>{currentLabel}</strong>{/if}
      </span>
    {/if}

    {#if refreshedAt}
      <span class="ml-auto text-gray-500 dark:text-gray-400 whitespace-nowrap">{refreshedAt}</span>
    {/if}
  </div>
</div>
