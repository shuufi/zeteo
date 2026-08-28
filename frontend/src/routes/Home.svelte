<script lang="ts">
  import { link } from 'svelte-spa-router';
  import PageHeader from '../lib/components/PageHeader.svelte';
  import ContextBar from '../lib/components/ContextBar.svelte';
  import KpiCard from '../lib/components/KpiCard.svelte';
  import {
    context,
    homeKpis,
    attentionException,
    topAdverseDrivers,
    topFavourableDrivers,
    leadingIndicators,
  } from '../lib/data/zeteo-data';
</script>

<PageHeader title="Home" />
<ContextBar refreshedAt={`Gold Layer refreshed ${context.refreshedAt}`} />

<div class="shell flex flex-col gap-5 pt-5 pb-12">
  <div class="grid grid-cols-6 gap-2.5">
    {#each homeKpis as kpi (kpi.id)}
      <KpiCard {kpi} />
    {/each}
  </div>

  <a
    class="block border-2 border-red-600 dark:border-red-400 rounded-lg py-2.5 px-4 bg-red-50 dark:bg-red-950 no-underline text-inherit hover:opacity-90"
    href="/diagnostic/{attentionException.targetNodeId}"
    use:link
  >
    <div class="flex justify-between items-baseline text-red-600 dark:text-red-400">
      <strong>Attention required</strong>
      <span
        class="inline-flex items-center justify-center w-[18px] h-[18px] rounded-full border-2 border-red-600 dark:border-red-400 text-[10px] font-bold bg-white dark:bg-gray-800"
        >1</span
      >
    </div>
    <div class="mt-1 text-base font-bold text-gray-900 dark:text-gray-50">
      {attentionException.title} — {attentionException.impact}
    </div>
    <div class="text-xs text-gray-500 dark:text-gray-400">
      {attentionException.explainedPct}% explained by three drivers ·
      <span
        class="border-[1.5px] border-dashed border-blue-600 dark:border-blue-400 text-blue-600 dark:text-blue-400 rounded-full px-2"
        >AI insight</span
      >
      · Investigate →
    </div>
  </a>

  <div class="flex gap-4">
    <div class="flex-1 border-[1.5px] border-gray-200 dark:border-gray-700 rounded-lg p-4 bg-white dark:bg-gray-800">
      <div class="font-bold text-sm mb-2">Top adverse drivers</div>
      {#each topAdverseDrivers as d (d.label)}
        {#if d.nodeId}
          <a
            class="flex justify-between py-1 text-sm no-underline text-inherit rounded hover:bg-gray-100 dark:hover:bg-gray-900"
            href="/vdt/{d.nodeId}"
            use:link
          >
            <span>{d.label}</span>
            <span class="text-red-600 dark:text-red-400">{d.amount}</span>
          </a>
        {:else}
          <div class="flex justify-between py-1 text-sm no-underline text-inherit rounded cursor-default">
            <span>{d.label}</span>
            <span class="text-red-600 dark:text-red-400">{d.amount}</span>
          </div>
        {/if}
      {/each}
    </div>
    <div class="flex-1 border-[1.5px] border-gray-200 dark:border-gray-700 rounded-lg p-4 bg-white dark:bg-gray-800">
      <div class="font-bold text-sm mb-2">Top favourable drivers</div>
      {#each topFavourableDrivers as d (d.label)}
        <div class="flex justify-between py-1 text-sm no-underline text-inherit rounded cursor-default">
          <span>{d.label}</span>
          <span class="text-green-600 dark:text-green-400">{d.amount}</span>
        </div>
      {/each}
    </div>
  </div>

  <div class="border-[1.5px] border-dashed border-blue-600 dark:border-blue-400 rounded-lg py-2.5 px-4">
    <div class="font-bold text-xs text-blue-600 dark:text-blue-400 mb-1">Leading indicators — signals ahead</div>
    <div class="flex gap-4 text-sm flex-wrap">
      {#each leadingIndicators as li (li.label)}
        <span>{li.label} {li.value}</span>
      {/each}
    </div>
  </div>
</div>
