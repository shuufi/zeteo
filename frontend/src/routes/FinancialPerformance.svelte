<script lang="ts">
  import { link } from 'svelte-spa-router';
  import PageHeader from '../lib/components/PageHeader.svelte';
  import ContextBar from '../lib/components/ContextBar.svelte';
  import KpiCard from '../lib/components/KpiCard.svelte';
  import GroupedBarChart from '../lib/components/GroupedBarChart.svelte';
  import ProfitBridge from '../lib/components/ProfitBridge.svelte';
  import {
    pnlRows,
    getNode,
    pct,
    formatVar,
    financialKpis,
    revenueCostOpexChart,
    profitBridgeSteps,
    getLargestPriorYearMovement,
  } from '../lib/data/zeteo-data';
  import type { PlLineItem, VdtNode } from '../lib/data/types';

  const rows = $derived(
    pnlRows
      .map((row) => ({ row, node: getNode(row.nodeId) }))
      .filter((r): r is { row: PlLineItem; node: VdtNode } => r.node !== undefined)
  );

  const insight = getLargestPriorYearMovement();

  function statementValue(actual: number, sign: 1 | -1): string {
    const text = actual.toFixed(1);
    return sign === -1 && actual !== 0 ? `(${text})` : text;
  }

  function varClass(row: PlLineItem, varPct: number): string {
    if (varPct === 0) return '';
    const favourable = row.sign === 1 ? varPct > 0 : varPct < 0;
    return favourable ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400';
  }
</script>

<PageHeader title="Financial Performance" />
<ContextBar currentLabel="Full P&L" />

<div class="shell flex flex-col gap-4 pt-5 pb-12">
  <div class="grid grid-cols-4 max-[900px]:grid-cols-2 gap-2.5">
    {#each financialKpis as kpi (kpi.id)}
      <KpiCard {kpi} />
    {/each}
  </div>

  <div class="flex max-[900px]:flex-col gap-4">
    <div class="flex-1 min-w-0 border border-gray-200 dark:border-gray-700 rounded-lg px-4 py-2.5 bg-white dark:bg-gray-800">
      <div class="font-bold text-sm mb-2 text-gray-900 dark:text-gray-50">Revenue, Cost of Revenue &amp; OPEX — Actual vs Prior Year</div>
      <GroupedBarChart categories={revenueCostOpexChart} width={420} />
    </div>
    <div class="flex-1 min-w-0 border border-gray-200 dark:border-gray-700 rounded-lg px-4 py-2.5 bg-white dark:bg-gray-800">
      <div class="font-bold text-sm mb-2 text-gray-900 dark:text-gray-50">Profit Bridge: Revenue to NPAT</div>
      <ProfitBridge steps={profitBridgeSteps} width={420} height={140} />
    </div>
  </div>

  <div class="border border-dashed border-indigo-600 dark:border-indigo-400 rounded-lg px-4 py-2.5 text-indigo-600 dark:text-indigo-400 text-sm">
    <strong>{insight.label}</strong> shows the largest movement vs prior year ({insight.pctLabel})
  </div>

  <div class="border border-gray-200 dark:border-gray-700 rounded-lg px-4 py-2.5 bg-white dark:bg-gray-800">
    <div class="flex justify-between items-baseline mb-2">
      <div class="font-bold text-sm text-gray-900 dark:text-gray-50">Full P&amp;L — FY26 Q3 YTD, shipping structure</div>
      <div class="text-xs text-gray-500 dark:text-gray-400">RM millions</div>
    </div>
    <div class="flex flex-col">
      <div class="grid grid-cols-[1.7fr_0.7fr_0.7fr_0.6fr_0.7fr_0.6fr] items-center py-1 text-xs text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-700">
        <span>Line item</span><span>Actual</span><span>Budget</span><span>vs Bgt</span><span>Prior Yr</span><span>vs LY</span>
      </div>
      {#each rows as { row, node } (row.nodeId)}
        {@const vsLy = node.priorYear !== undefined ? pct(node.actual, node.priorYear) : undefined}
        <a
          class="grid grid-cols-[1.7fr_0.7fr_0.7fr_0.6fr_0.7fr_0.6fr] items-center py-1 text-sm no-underline text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-900 {row.isSubtotal ? 'font-bold bg-gray-100 dark:bg-gray-800 rounded' : ''} {row.isFinal ? 'bg-gray-900 dark:bg-gray-50 text-white dark:text-gray-800 rounded pl-1.5' : ''}"
          href="/vdt/{row.nodeId}"
          use:link
        >
          <span class={row.indent === 1 ? 'pl-4 text-gray-500 dark:text-gray-400' : undefined}>{row.label}</span>
          <span>{statementValue(node.actual, row.sign)}</span>
          <span>{statementValue(node.budget, row.sign)}</span>
          <span class={varClass(row, node.varPct)}>{formatVar(node.varPct)}</span>
          <span>{node.priorYear !== undefined ? statementValue(node.priorYear, row.sign) : '—'}</span>
          <span class={vsLy !== undefined ? varClass(row, vsLy) : ''}>
            {vsLy !== undefined ? formatVar(vsLy) : '—'}
          </span>
        </a>
      {/each}
    </div>
    <div class="text-[10px] text-indigo-600 dark:text-indigo-400 mt-2">click any line → opens VDT Explorer scoped to that line, subtotal rows → opens the decomposition one level down into their own children</div>
  </div>
</div>
