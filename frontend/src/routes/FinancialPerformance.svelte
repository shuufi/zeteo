<script lang="ts">
  import { link } from 'svelte-spa-router';
  import PageHeader from '../lib/components/PageHeader.svelte';
  import PageBody from '../lib/components/PageBody.svelte';
  import ContextBar from '../lib/components/ContextBar.svelte';
  import KpiCard from '../lib/components/KpiCard.svelte';
  import MonthlyTrendChart from '../lib/components/MonthlyTrendChart.svelte';
  import ProfitBridge from '../lib/components/ProfitBridge.svelte';
  import {
    pnlRows,
    getNode,
    getMonthlyPnl,
    cumulative,
    financialKpis,
    months,
    monthlyPerformanceChart,
    profitBridgeSteps,
  } from '../lib/data/zeteo-data';
  import type { PlLineItem, VdtNode } from '../lib/data/types';

  let ytdView = $state(false);

  const rows = $derived(
    pnlRows
      .map((row) => ({ row, node: getNode(row.nodeId), monthly: getMonthlyPnl(row.nodeId) ?? [] }))
      .filter((r): r is { row: PlLineItem; node: VdtNode; monthly: number[] } => r.node !== undefined)
  );

  const displayRows = $derived(
    rows.map((r) => ({ ...r, values: ytdView ? cumulative(r.monthly) : r.monthly }))
  );

  const statementGridCols = 'grid-cols-[minmax(240px,1.3fr)_repeat(12,minmax(64px,1fr))]';

  function statementValue(actual: number, sign: 1 | -1): string {
    const text = actual.toFixed(1);
    return sign === -1 && actual !== 0 ? `(${text})` : text;
  }
</script>

<PageHeader title="Financial Performance" />
<PageBody>
  <ContextBar />

  <div class="flex flex-col gap-4 pt-4">
  <div class="grid grid-cols-4 max-[900px]:grid-cols-2 gap-2.5">
    {#each financialKpis as kpi (kpi.id)}
      <KpiCard {kpi} />
    {/each}
  </div>

  <div class="flex max-[900px]:flex-col gap-4">
    <div class="flex-1 min-w-0 border border-gray-200 dark:border-gray-700 rounded-lg px-4 py-2.5 bg-white dark:bg-gray-800">
      <div class="font-bold text-sm mb-2 text-gray-900 dark:text-gray-50">Revenue, Cost of Revenue &amp; OPEX — Monthly Trend</div>
      <MonthlyTrendChart series={monthlyPerformanceChart} {months} width={420} />
    </div>
    <div class="flex-1 min-w-0 border border-gray-200 dark:border-gray-700 rounded-lg px-4 py-2.5 bg-white dark:bg-gray-800">
      <div class="font-bold text-sm mb-2 text-gray-900 dark:text-gray-50">Profit Bridge: Revenue to NPAT</div>
      <ProfitBridge steps={profitBridgeSteps} width={420} height={140} />
    </div>
  </div>

  <div class="border border-gray-200 dark:border-gray-700 rounded-lg px-4 py-2.5 bg-white dark:bg-gray-800">
    <div class="flex justify-between items-baseline mb-2">
      <div class="font-bold text-sm text-gray-900 dark:text-gray-50">Full P&amp;L — {ytdView ? 'YTD' : 'Monthly'} Trend, shipping structure</div>
      <div class="flex items-center gap-3">
        <label class="flex items-center gap-1.5 text-xs text-gray-600 dark:text-gray-300 cursor-pointer select-none">
          <input type="checkbox" bind:checked={ytdView} class="accent-indigo-600 dark:accent-indigo-400" />
          YTD (cumulative)
        </label>
        <div class="text-xs text-gray-500 dark:text-gray-400">RM millions</div>
      </div>
    </div>
    <div class="overflow-x-auto">
      <div class="flex flex-col min-w-[1080px]">
        <div class="grid {statementGridCols} items-center py-1 text-xs text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-700">
          <span>Line item</span>
          {#each months as m (m)}
            <span class="text-right">{m}</span>
          {/each}
        </div>
        {#each displayRows as { row, values } (row.nodeId)}
          <a
            class="grid {statementGridCols} items-center py-1.5 text-sm no-underline text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-900 {row.isSubtotal ? 'font-bold bg-gray-100 dark:bg-gray-800 rounded' : ''} {row.isFinal ? 'bg-gray-900 dark:bg-gray-50 text-white dark:text-gray-800 rounded pl-1.5' : ''}"
            href="/vdt/{row.nodeId}"
            use:link
          >
            <span class={row.indent === 1 ? 'pl-4 text-gray-500 dark:text-gray-400' : undefined}>{row.label}</span>
            {#each values as value, i (i)}
              <span class="text-right tabular-nums">{statementValue(value, row.sign)}</span>
            {/each}
          </a>
        {/each}
      </div>
    </div>
    <div class="text-[10px] text-indigo-600 dark:text-indigo-400 mt-2">click any line → opens VDT Explorer scoped to that line, subtotal rows → opens the decomposition one level down into their own children</div>
  </div>
  </div>
</PageBody>
