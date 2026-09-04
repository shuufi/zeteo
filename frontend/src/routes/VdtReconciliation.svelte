<script lang="ts">
  import { onMount } from "svelte";
  import PageHeader from "../lib/components/PageHeader.svelte";
  import PageBody from "../lib/components/PageBody.svelte";
  import ContextBar from "../lib/components/ContextBar.svelte";
  import Card from "../lib/components/Card.svelte";
  import NotYetModelled from "../lib/components/NotYetModelled.svelte";
  import LottieLoader from "../lib/components/LottieLoader.svelte";
  import StatementTable, { type StatementColumn } from "../lib/components/StatementTable.svelte";
  import { scopeState } from "../lib/state/scope.svelte";
  import { periodState } from "../lib/state/period.svelte";
  import { reconciliationStore, loadReconciliation } from "../lib/data/reconciliation-store.svelte";
  import { getNode, buildDisplayRows } from "../lib/data/gl-client";
  import { loadPeriods } from "../lib/data/period-store.svelte";
  import { hierarchyMoneyValues, moneyCaption, resolveMoneyScale, type MoneyScaleChoice } from "../lib/data/format";
  import type { DisplayRow } from "../lib/data/types";

  onMount(loadPeriods);

  // Fixed anchor — same root VDT Explorer's own statement uses (the only
  // branch with real VDT data seeded). No node picker: see docs/adr/0037.
  const RECONCILIATION_ROOT = "V201000000";
  let moneyScale = $state<MoneyScaleChoice>("auto");
  let ytd = $state(true);

  $effect(() => {
    const scope = scopeState.code;
    const period = periodState.code;
    loadReconciliation(scope, RECONCILIATION_ROOT, period, ytd);
  });

  const rows = $derived(buildDisplayRows(reconciliationStore.vdtTree, RECONCILIATION_ROOT));

  // Only a Posting Activity Account leaf carries a real Accounting
  // counterpart, via its FA GL anchor (see docs/adr/0033) — everything else
  // (Activity Node rows, including the root, and Driver/Formula rows) has no
  // same-code Accounting node, so its GL/Delta cells stay blank rather than
  // inventing a rollup (see docs/adr/0037).
  function accountingActual(row: DisplayRow): number | undefined {
    const node = getNode(reconciliationStore.vdtTree, row.nodeId);
    if (node?.nodeType !== "Posting Activity Account" || !node.faGlCode) return undefined;
    return getNode(reconciliationStore.accountingTree, node.faGlCode)?.actual;
  }

  function cellValue(row: DisplayRow, column: StatementColumn): number | null {
    const vdt = getNode(reconciliationStore.vdtTree, row.nodeId)?.actual ?? 0;
    if (column.key === "vdt") return vdt;
    const gl = accountingActual(row);
    if (column.key === "gl") return gl ?? null;
    return gl === undefined ? null : vdt - gl;
  }

  const moneyValues = $derived([
    ...hierarchyMoneyValues(reconciliationStore.vdtTree, RECONCILIATION_ROOT),
    ...rows.map(accountingActual).filter((v): v is number => v !== undefined),
  ]);
  const resolvedMoneyScale = $derived(resolveMoneyScale(moneyScale, moneyValues));
  const currency = $derived(reconciliationStore.meta?.currency ?? "");
  const columns = $derived<StatementColumn[]>([
    { key: "vdt", label: "VDT" },
    { key: "gl", label: "Accounting GL" },
    { key: "delta", label: "Delta" },
  ]);
</script>

<PageHeader title="VDT Reconciliation" />
<PageBody>
  <ContextBar showYtd bind:ytd showComparisonChip={false} showMoneyScale {currency} {moneyValues} bind:moneyScale />

  {#if reconciliationStore.status === "loading"}
    <div class="pt-4 flex-1 min-w-0 flex flex-col items-center justify-center gap-2">
      <LottieLoader size={160} />
      <div class="text-sm text-gray-500 dark:text-gray-400">Loading…</div>
    </div>
  {:else if reconciliationStore.status === "not-yet-modelled"}
    <div class="pt-4">
      <NotYetModelled label="No data modelled for the selected company yet." />
    </div>
  {:else if reconciliationStore.status === "ready"}
    <div class="pt-4 min-w-0">
      <Card>
        {#snippet header()}
          <div class="flex justify-between items-baseline mb-2">
            <div class="font-bold text-sm text-gray-900 dark:text-gray-50">SOC Crew Cost</div>
            <div class="text-xs text-gray-500 dark:text-gray-400">{moneyCaption(currency, resolvedMoneyScale)}</div>
          </div>
        {/snippet}
        <StatementTable
          {rows}
          {columns}
          {cellValue}
          resizable
          showLabelTooltip
          {currency}
          moneyScale={resolvedMoneyScale}
        />
      </Card>
    </div>
  {/if}
</PageBody>
