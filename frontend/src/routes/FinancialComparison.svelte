<script lang="ts">
  import { onMount } from 'svelte';
  import { slide } from 'svelte/transition';
  import PageHeader from '../lib/components/PageHeader.svelte';
  import PageBody from '../lib/components/PageBody.svelte';
  import ContextBar from '../lib/components/ContextBar.svelte';
  import Card from '../lib/components/Card.svelte';
  import ProfitBridge from '../lib/components/ProfitBridge.svelte';
  import NotYetModelled from '../lib/components/NotYetModelled.svelte';
  import { scopeState } from '../lib/state/scope.svelte';
  import { comparisonStore, loadComparison } from '../lib/data/comparison-store.svelte';
  import { getComparisonNode, getComparisonChildren, buildComparisonRows } from '../lib/data/comparison-client';
  import { indentClass } from '../lib/data/gl-client';
  import { loadPeriods, periodLabel } from '../lib/data/period-store.svelte';
  import type { DisplayRow, OperationalUnit, PeriodType, Direction, BridgeStep, ComparisonNode } from '../lib/data/types';

  onMount(loadPeriods);

  let comparisonNodeId = $state<string | undefined>('NPAT');
  let grain = $state<PeriodType>('Month');
  let periodA = $state<string | undefined>(undefined);
  let periodB = $state<string | undefined>(undefined);

  $effect(() => {
    const node = comparisonNodeId;
    const a = periodA;
    const b = periodB;
    const scope = scopeState.code;
    if (!node || !a || !b) return;
    loadComparison(scope, node, a, b);
  });

  const comparisonRoot = $derived(comparisonNodeId ? getComparisonNode(comparisonStore.tree, comparisonNodeId) : undefined);

  function bridgeKind(direction: Direction): BridgeStep['kind'] {
    return direction === 'favourable' ? 'increase' : direction === 'adverse' ? 'decrease' : 'neutral';
  }

  // Bridge bars are the comparison node's direct GL children only — Driver/
  // Driver Formula children (non-RM units) belong in the table, not a bridge
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
  const rowsByNodeId = $derived(new Map(comparisonRows.map((row) => [row.nodeId, row])));
  const collapsibleIds = $derived(new Set(comparisonRows.map((row) => row.group).filter((g): g is string => g !== undefined)));
  const operationalGroupIds = $derived(
    new Set(
      comparisonRows
        .filter((row) => row.kind === 'operational')
        .map((row) => row.group)
        .filter((g): g is string => g !== undefined),
    ),
  );
  const summaryGroupIds = $derived(new Set([...collapsibleIds].filter((id) => (rowsByNodeId.get(id)?.indent ?? 0) < 1)));

  let expandedGroups = $state<Set<string>>(new Set());
  let expandedGroupsInitialised = false;
  $effect(() => {
    if (expandedGroupsInitialised || comparisonRows.length === 0) return;
    expandedGroupsInitialised = true;
    expandedGroups = new Set([...summaryGroupIds].filter((id) => !operationalGroupIds.has(id)));
  });
  // Re-run initial-collapse whenever the comparison node itself changes.
  $effect(() => {
    comparisonNodeId;
    expandedGroupsInitialised = false;
  });

  function toggleGroup(nodeId: string): void {
    const next = new Set(expandedGroups);
    if (next.has(nodeId)) next.delete(nodeId);
    else next.add(nodeId);
    expandedGroups = next;
  }

  function isVisible(row: DisplayRow): boolean {
    let group = row.group;
    while (group) {
      if (!expandedGroups.has(group)) return false;
      group = rowsByNodeId.get(group)?.group;
    }
    return true;
  }

  const visibleRows = $derived(
    comparisonRows
      .filter(isVisible)
      .map((row) => ({ row, node: getComparisonNode(comparisonStore.tree, row.nodeId) }))
      .filter((r): r is { row: DisplayRow; node: ComparisonNode } => r.node !== undefined),
  );

  // Values already carry the right sign server-side (see docs/adr/0023) — a
  // negative number is a subtraction/loss, shown in parens.
  function statementValue(value: number): string {
    const text = Math.abs(value).toFixed(1);
    return value < 0 && value !== 0 ? `(${text})` : text;
  }

  function operationalValue(value: number, unit: OperationalUnit | 'RM_M' | undefined): string {
    switch (unit) {
      case 'RM_M':
        return statementValue(value);
      case 'usd-per-day':
        return value < 10 ? `$${value.toFixed(3)}k/d` : `$${value.toFixed(0)}k/d`;
      case 'usd-per-month':
        return value < 10 ? `$${value.toFixed(3)}k/mo` : `$${value.toFixed(0)}k/mo`;
      case 'percent':
        return `${value.toFixed(1)}%`;
      case 'days':
        return value.toFixed(1);
      case 'count':
        return value.toFixed(0);
      case 'ratio':
        return `${value.toFixed(2)}×`;
      default:
        return value.toFixed(1);
    }
  }

  function deltaPctLabel(deltaPct: number | null): string {
    if (deltaPct === null) return '';
    const sign = deltaPct > 0 ? '+' : '';
    return ` (${sign}${deltaPct.toFixed(1)}%)`;
  }

  // Favourable/adverse only applies to GL rows (see docs/adr/0031) — operational
  // (Driver/Formula) rows always render their delta neutral, regardless of sign.
  function deltaClass(row: DisplayRow, direction: Direction): string {
    if (row.kind === 'operational') return 'text-gray-500 dark:text-gray-400';
    if (direction === 'favourable') return 'text-emerald-600 dark:text-emerald-400';
    if (direction === 'adverse') return 'text-red-600 dark:text-red-400';
    return 'text-gray-500 dark:text-gray-400';
  }

  const gridTemplateColumns = '1fr repeat(3, minmax(110px,1fr))';

  const grains: PeriodType[] = ['Month', 'Quarter', 'Year'];
</script>

{#snippet operationalCells(row: DisplayRow, node: ComparisonNode, isCollapsible: boolean)}
  <span class="{indentClass(row.indent)} flex flex-col min-w-0">
    <span class="flex items-center gap-1.5 min-w-0">
      {#if isCollapsible}
        <span
          class="inline-block w-4 shrink-0 text-base leading-none text-amber-600 dark:text-amber-400 transition-transform duration-150 {expandedGroups.has(row.nodeId) ? 'rotate-90' : ''}"
        >
          ▸
        </span>
      {/if}
      <span
        class="text-[9px] uppercase tracking-wide font-semibold text-amber-600 dark:text-amber-400 border border-amber-300 dark:border-amber-400/40 rounded px-1 shrink-0"
        >{row.driverNodeType === 'formula' ? 'Formula' : 'Ops'}</span
      >
      <span class="truncate">{row.label}</span>
    </span>
    {#if row.driverNodeType === 'formula' && row.expression}
      <span class="truncate text-[10px] font-normal normal-case tracking-normal text-amber-600/70 dark:text-amber-400/60 {isCollapsible ? 'pl-6' : ''}" title={row.expression}>
        {row.expression}
      </span>
    {/if}
  </span>
  <span class="text-right tabular-nums">{operationalValue(node.valueA, row.unit)}</span>
  <span class="text-right tabular-nums">{operationalValue(node.valueB, row.unit)}</span>
  <span class="text-right tabular-nums {deltaClass(row, node.direction)}">
    {operationalValue(node.delta, row.unit)}{deltaPctLabel(node.deltaPct)}
  </span>
{/snippet}

<PageHeader title="Financial Comparison" />
<PageBody>
  <ContextBar showYtd={false} showPeriod={false} showComparison bind:comparisonNode={comparisonNodeId} bind:grain bind:periodA bind:periodB />

  {#if !comparisonNodeId || !periodA || !periodB}
    <div class="pt-4 text-sm text-gray-500 dark:text-gray-400">Pick a comparison node and two periods to compare.</div>
  {:else if comparisonStore.status === 'loading'}
    <div class="pt-4">Loading…</div>
  {:else if comparisonStore.status === 'not-yet-modelled'}
    <div class="pt-4">
      <NotYetModelled label="No GL data modelled for the selected company/BU yet." />
    </div>
  {:else if comparisonRoot}
    <div class="flex flex-col gap-4 pt-2">
      <Card title="Change from {periodLabel(comparisonStore.meta?.periodA ?? '')} to {periodLabel(comparisonStore.meta?.periodB ?? '')}">
        <ProfitBridge steps={deltaBridgeSteps} height={Math.max(220, deltaBridgeSteps.length * 32)} />
      </Card>

      <Card>
        {#snippet header()}
          <div class="flex justify-between items-baseline mb-2">
            <div class="font-bold text-sm text-gray-900 dark:text-gray-50">{comparisonRoot.name}</div>
            <div class="text-xs text-gray-500 dark:text-gray-400">RM millions</div>
          </div>
        {/snippet}
        <div class="overflow-x-auto">
          <div class="flex flex-col min-w-[640px]">
            <div
              class="grid items-center py-1 text-xs text-indigo-700 dark:text-indigo-300 border-b border-indigo-200 dark:border-indigo-900"
              style="grid-template-columns: {gridTemplateColumns}"
            >
              <span>Line item</span>
              <span class="text-right">{periodLabel(comparisonStore.meta?.periodA ?? '')}</span>
              <span class="text-right">{periodLabel(comparisonStore.meta?.periodB ?? '')}</span>
              <span class="text-right">Δ</span>
            </div>

            {#each visibleRows as { row, node } (row.nodeId)}
              {#if row.kind === 'operational'}
                {#if collapsibleIds.has(row.nodeId)}
                  <div
                    role="button"
                    tabindex="0"
                    onclick={() => toggleGroup(row.nodeId)}
                    onkeydown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        toggleGroup(row.nodeId);
                      }
                    }}
                    transition:slide={{ duration: 150 }}
                    class="grid items-center py-1.5 text-sm cursor-pointer text-amber-700 dark:text-amber-400 bg-amber-50/60 dark:bg-amber-400/10"
                    style="grid-template-columns: {gridTemplateColumns}"
                  >
                    {@render operationalCells(row, node, true)}
                  </div>
                {:else}
                  <div transition:slide={{ duration: 150 }} class="grid items-center py-1.5 text-sm text-amber-700 dark:text-amber-400 bg-amber-50/60 dark:bg-amber-400/10" style="grid-template-columns: {gridTemplateColumns}">
                    {@render operationalCells(row, node, false)}
                  </div>
                {/if}
              {:else if collapsibleIds.has(row.nodeId)}
                <div
                  role="button"
                  tabindex="0"
                  onclick={() => toggleGroup(row.nodeId)}
                  onkeydown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      toggleGroup(row.nodeId);
                    }
                  }}
                  transition:slide={{ duration: 150 }}
                  class="grid items-center py-1.5 text-sm cursor-pointer text-gray-700 dark:text-gray-300 hover:bg-indigo-50 dark:hover:bg-indigo-950/40 {row.isSubtotal ? 'font-bold bg-indigo-50 dark:bg-indigo-900/30 rounded' : ''}"
                  style="grid-template-columns: {gridTemplateColumns}"
                >
                  <span class="flex items-center gap-1.5 min-w-0 {indentClass(row.indent)} {row.indent > 0 ? 'text-gray-500 dark:text-gray-400' : ''}">
                    <span
                      class="inline-block w-4 shrink-0 text-base leading-none text-indigo-600 dark:text-indigo-400 transition-transform duration-150 {expandedGroups.has(row.nodeId) ? 'rotate-90' : ''}"
                    >
                      ▸
                    </span>
                    <span class="truncate">{row.label}</span>
                  </span>
                  <span class="text-right tabular-nums">{statementValue(node.valueA)}</span>
                  <span class="text-right tabular-nums">{statementValue(node.valueB)}</span>
                  <span class="text-right tabular-nums {deltaClass(row, node.direction)}">
                    {statementValue(node.delta)}{deltaPctLabel(node.deltaPct)}
                  </span>
                </div>
              {:else}
                <div
                  transition:slide={{ duration: 150 }}
                  class="grid items-center py-1.5 text-sm text-gray-700 dark:text-gray-300 hover:bg-indigo-50 dark:hover:bg-indigo-950/40 {row.isSubtotal ? 'font-bold bg-indigo-50 dark:bg-indigo-900/30 rounded' : ''} {row.isFinal ? 'bg-indigo-600 dark:bg-indigo-500 text-white rounded pl-1.5' : ''}"
                  style="grid-template-columns: {gridTemplateColumns}"
                >
                  <span class="flex min-w-0 {row.indent > 0 ? `${indentClass(row.indent)} text-gray-500 dark:text-gray-400` : ''}">
                    <span class="truncate">{row.label}</span>
                  </span>
                  <span class="text-right tabular-nums">{statementValue(node.valueA)}</span>
                  <span class="text-right tabular-nums">{statementValue(node.valueB)}</span>
                  <span class="text-right tabular-nums {row.isFinal ? '' : deltaClass(row, node.direction)}">
                    {statementValue(node.delta)}{deltaPctLabel(node.deltaPct)}
                  </span>
                </div>
              {/if}
            {/each}
          </div>
        </div>
      </Card>
    </div>
  {/if}
</PageBody>
