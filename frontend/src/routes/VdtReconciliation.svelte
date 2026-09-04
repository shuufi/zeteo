<script lang="ts">
  import { onMount } from "svelte";
  import PageHeader from "../lib/components/PageHeader.svelte";
  import PageBody from "../lib/components/PageBody.svelte";
  import ContextBar from "../lib/components/ContextBar.svelte";
  import Card from "../lib/components/Card.svelte";
  import NotYetModelled from "../lib/components/NotYetModelled.svelte";
  import StatementTable, { type StatementColumn } from "../lib/components/StatementTable.svelte";
  import { scopeState } from "../lib/state/scope.svelte";
  import { periodState } from "../lib/state/period.svelte";
  import { reconciliationStore, loadReconciliation } from "../lib/data/reconciliation-store.svelte";
  import { getNode, buildDisplayRows } from "../lib/data/gl-client";
  import { loadPeriods } from "../lib/data/period-store.svelte";
  import {
    formatMoney,
    hierarchyMoneyValues,
    moneyCaption,
    resolveMoneyScale,
    type MoneyScaleChoice,
  } from "../lib/data/format";
  import type { DisplayRow } from "../lib/data/types";

  onMount(loadPeriods);

  // Restricted to Reporting Root/Reporting Node types (same restriction
  // Comparison's NodePicker already imposes) — only those are guaranteed to
  // exist under the same code in both hierarchies, see docs/adr/0033.
  let reconciliationNodeId = $state<string | undefined>("PNL-0011");
  let moneyScale = $state<MoneyScaleChoice>("auto");

  $effect(() => {
    const node = reconciliationNodeId;
    const scope = scopeState.code;
    const period = periodState.code;
    if (!node) return;
    loadReconciliation(scope, node, period);
  });

  const accountingRows = $derived(
    reconciliationNodeId ? buildDisplayRows(reconciliationStore.accountingTree, reconciliationNodeId) : [],
  );
  const vdtRows = $derived(
    reconciliationNodeId ? buildDisplayRows(reconciliationStore.vdtTree, reconciliationNodeId) : [],
  );

  const moneyValues = $derived([
    ...hierarchyMoneyValues(reconciliationStore.accountingTree, reconciliationNodeId),
    ...hierarchyMoneyValues(reconciliationStore.vdtTree, reconciliationNodeId),
  ]);
  const resolvedMoneyScale = $derived(resolveMoneyScale(moneyScale, moneyValues));
  const currency = $derived(reconciliationStore.meta?.currency ?? "");
  const singleColumn = $derived<StatementColumn[]>([{ key: "value", label: moneyCaption(currency, resolvedMoneyScale) }]);

  let lastScaleNode = "";
  $effect(() => {
    const node = reconciliationNodeId ?? "";
    if (lastScaleNode && node !== lastScaleNode) moneyScale = "auto";
    lastScaleNode = node;
  });

  function accountingCellValue(row: DisplayRow): number {
    return getNode(reconciliationStore.accountingTree, row.nodeId)?.actual ?? 0;
  }
  function vdtCellValue(row: DisplayRow): number {
    return getNode(reconciliationStore.vdtTree, row.nodeId)?.actual ?? 0;
  }
  function accountingRowExists(row: DisplayRow): boolean {
    return row.kind === "operational" || getNode(reconciliationStore.accountingTree, row.nodeId) !== undefined;
  }
  function vdtRowExists(row: DisplayRow): boolean {
    return row.kind === "operational" || getNode(reconciliationStore.vdtTree, row.nodeId) !== undefined;
  }

  const accountingTotal = $derived(
    reconciliationNodeId ? getNode(reconciliationStore.accountingTree, reconciliationNodeId)?.actual : undefined,
  );
  const vdtTotal = $derived(
    reconciliationNodeId ? getNode(reconciliationStore.vdtTree, reconciliationNodeId)?.actual : undefined,
  );
  const gap = $derived(
    accountingTotal !== undefined && vdtTotal !== undefined ? vdtTotal - accountingTotal : undefined,
  );
</script>

<PageHeader title="VDT Reconciliation" />
<PageBody>
  <ContextBar
    showReconciliation
    bind:reconciliationNode={reconciliationNodeId}
    showMoneyScale
    {currency}
    {moneyValues}
    bind:moneyScale
  />

  {#if !reconciliationNodeId}
    <div class="pt-4 text-sm text-gray-500 dark:text-gray-400">Pick a node to reconcile.</div>
  {:else if reconciliationStore.status === "loading"}
    <div class="pt-4">Loading…</div>
  {:else if reconciliationStore.status === "not-yet-modelled"}
    <div class="pt-4">
      <NotYetModelled label="No data modelled for the selected company yet." />
    </div>
  {:else if reconciliationStore.status === "ready"}
    <div class="flex flex-col gap-4 pt-2 min-w-0">
      {#if accountingTotal !== undefined && vdtTotal !== undefined && gap !== undefined}
        <div class="text-xs text-gray-500 dark:text-gray-400">
          Accounting: <span class="font-semibold text-gray-700 dark:text-gray-300">{formatMoney(accountingTotal, currency, resolvedMoneyScale)}</span>
          · VDT: <span class="font-semibold text-gray-700 dark:text-gray-300">{formatMoney(vdtTotal, currency, resolvedMoneyScale)}</span>
          · Gap:
          <span class="font-semibold {gap === 0 ? '' : 'text-amber-600 dark:text-amber-400'}">{formatMoney(gap, currency, resolvedMoneyScale)}</span>
          — VDT is an independent, activity-based estimate here, not required to reconcile to the ledger.
        </div>
      {/if}
      <div class="flex max-[900px]:flex-col gap-4 min-w-0">
        <Card class="flex-1 min-w-0" title="Accounting">
          <StatementTable
            rows={accountingRows}
            columns={singleColumn}
            cellValue={accountingCellValue}
            rowExists={accountingRowExists}
            columnMinWidthPx={110}
            minTableWidthPx={360}
            resetKey={reconciliationNodeId}
            {currency}
            moneyScale={resolvedMoneyScale}
          />
        </Card>
        <Card class="flex-1 min-w-0" title="VDT">
          <StatementTable
            rows={vdtRows}
            columns={singleColumn}
            cellValue={vdtCellValue}
            rowExists={vdtRowExists}
            columnMinWidthPx={110}
            minTableWidthPx={360}
            resetKey={reconciliationNodeId}
            {currency}
            moneyScale={resolvedMoneyScale}
          />
        </Card>
      </div>
    </div>
  {/if}
</PageBody>
