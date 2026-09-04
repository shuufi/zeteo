<script lang="ts">
  import { onMount } from 'svelte';
  import PageHeader from '../lib/components/PageHeader.svelte';
  import PageBody from '../lib/components/PageBody.svelte';
  import ContextBar from '../lib/components/ContextBar.svelte';
  import Card from '../lib/components/Card.svelte';
  import ProfitBridge from '../lib/components/ProfitBridge.svelte';
  import NotYetModelled from '../lib/components/NotYetModelled.svelte';
  import StatementTable, { type StatementColumn } from '../lib/components/StatementTable.svelte';
  import { scopeState } from '../lib/state/scope.svelte';
  import { comparisonStore, loadComparison } from '../lib/data/comparison-store.svelte';
  import { getComparisonNode, getComparisonChildren, buildComparisonRows } from '../lib/data/comparison-client';
  import { loadPeriods, periodLabel } from '../lib/data/period-store.svelte';
  import { comparisonMoneyValues, moneyCaption, resolveMoneyScale, type MoneyScaleChoice } from '../lib/data/format';
  import type { DisplayRow, PeriodType, Direction, BridgeStep } from '../lib/data/types';

  onMount(loadPeriods);

  let comparisonNodeId = $state<string | undefined>('NPAT');
  let grain = $state<PeriodType>('Month');
  let bridgeEmphasis = $state(0.7);
  let periodA = $state<string | undefined>(undefined);
  let periodB = $state<string | undefined>(undefined);
  let moneyScale = $state<MoneyScaleChoice>('auto');

  $effect(() => {
    const node = comparisonNodeId;
    const a = periodA;
    const b = periodB;
    const scope = scopeState.code;
    if (!node || !a || !b) return;
    loadComparison(scope, node, a, b);
  });

  const comparisonRoot = $derived(comparisonNodeId ? getComparisonNode(comparisonStore.tree, comparisonNodeId) : undefined);
  const moneyValues = $derived(comparisonNodeId ? comparisonMoneyValues(comparisonStore.tree, comparisonNodeId) : []);
  const resolvedMoneyScale = $derived(resolveMoneyScale(moneyScale, moneyValues));
  const currency = $derived(comparisonStore.meta?.currency ?? '');

  let lastScaleDataKey = '';
  $effect(() => {
    const key = `${comparisonNodeId ?? ''}:${periodA ?? ''}:${periodB ?? ''}`;
    if (lastScaleDataKey && key !== lastScaleDataKey) moneyScale = 'auto';
    lastScaleDataKey = key;
  });

  function bridgeKind(direction: Direction): BridgeStep['kind'] {
    return direction === 'favourable' ? 'increase' : direction === 'adverse' ? 'decrease' : 'neutral';
  }

  // Bridge bars are the comparison node's direct GL children only — Driver/
  // Driver Formula children (non-money units) belong in the table, not a bridge
  // (see docs/adr/0031). In practice a Reporting Root/Node's direct children
  // are always GL-typed anyway (Q13's picker restriction), this filter is
  // just defensive.
  const deltaBridgeSteps = $derived<BridgeStep[]>(
    comparisonRoot
      ? [
          { label: periodLabel(comparisonStore.meta?.periodA ?? periodA ?? ''), value: comparisonRoot.valueA, kind: 'total' },
          ...getComparisonChildren(comparisonStore.tree, comparisonRoot)
            .filter((c) => c.nodeType !== 'Driver Formula' && c.nodeType !== 'Driver')
            .map((c) => ({ label: c.name, value: c.delta, kind: bridgeKind(c.direction) })),
          { label: periodLabel(comparisonStore.meta?.periodB ?? periodB ?? ''), value: comparisonRoot.valueB, kind: 'total' as const },
        ]
      : [],
  );

  const comparisonRows = $derived(comparisonNodeId ? buildComparisonRows(comparisonStore.tree, comparisonNodeId) : []);

  const columns = $derived<StatementColumn[]>([
    { key: 'A', label: periodLabel(comparisonStore.meta?.periodA ?? '') },
    { key: 'B', label: periodLabel(comparisonStore.meta?.periodB ?? '') },
    { key: 'delta', label: 'Δ', isDelta: true },
  ]);

  function cellValue(row: DisplayRow, column: StatementColumn): number {
    const node = getComparisonNode(comparisonStore.tree, row.nodeId);
    if (!node) return 0;
    if (column.key === 'A') return node.valueA;
    if (column.key === 'B') return node.valueB;
    return node.delta;
  }

  function cellDirection(row: DisplayRow): Direction {
    return getComparisonNode(comparisonStore.tree, row.nodeId)?.direction ?? 'neutral';
  }

  function cellDeltaPct(row: DisplayRow): number | null {
    return getComparisonNode(comparisonStore.tree, row.nodeId)?.deltaPct ?? null;
  }

  function rowExists(row: DisplayRow): boolean {
    return getComparisonNode(comparisonStore.tree, row.nodeId) !== undefined;
  }

  const grains: PeriodType[] = ['Month', 'Quarter', 'Year'];
</script>

<PageHeader title="Financial Comparison" />
<PageBody>
  <ContextBar
    showYtd={false}
    showPeriod={false}
    showComparison
    bind:comparisonNode={comparisonNodeId}
    bind:grain
    bind:periodA
    bind:periodB
    showMoneyScale
    {currency}
    {moneyValues}
    bind:moneyScale
  />

  {#if !comparisonNodeId || !periodA || !periodB}
    <div class="pt-4 text-sm text-gray-500 dark:text-gray-400">Pick a comparison node and two periods to compare.</div>
  {:else if comparisonStore.status === 'loading'}
    <div class="pt-4">Loading…</div>
  {:else if comparisonStore.status === 'not-yet-modelled'}
    <div class="pt-4">
      <NotYetModelled label="No GL data modelled for the selected company yet." />
    </div>
  {:else if comparisonRoot}
    <div class="flex flex-col gap-4 pt-2 min-w-0">
      <Card>
        {#snippet header()}
          <div class="flex flex-wrap items-center justify-between gap-3 mb-2">
            <div class="font-bold text-sm text-gray-900 dark:text-gray-50">
              Change from {periodLabel(comparisonStore.meta?.periodA ?? '')} to {periodLabel(comparisonStore.meta?.periodB ?? '')}
            </div>
            <label class="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400 select-none">
              Emphasize changes
              <input type="range" min="0" max="1" step="0.05" bind:value={bridgeEmphasis} class="accent-indigo-600 dark:accent-indigo-400" />
            </label>
          </div>
        {/snippet}
        <ProfitBridge steps={deltaBridgeSteps} emphasis={bridgeEmphasis} {currency} moneyScale={resolvedMoneyScale} />
      </Card>

      <Card>
        {#snippet header()}
          <div class="flex justify-between items-baseline mb-2">
            <div class="font-bold text-sm text-gray-900 dark:text-gray-50">{comparisonRoot.name}</div>
            <div class="text-xs text-gray-500 dark:text-gray-400">{moneyCaption(currency, resolvedMoneyScale)}</div>
          </div>
        {/snippet}
        <StatementTable
          rows={comparisonRows}
          {columns}
          {cellValue}
          {rowExists}
          {cellDirection}
          {cellDeltaPct}
          showDeltaColoring
          columnMinWidthPx={110}
          minTableWidthPx={640}
          resetKey={comparisonNodeId}
          {currency}
          moneyScale={resolvedMoneyScale}
        />
      </Card>
    </div>
  {/if}
</PageBody>
