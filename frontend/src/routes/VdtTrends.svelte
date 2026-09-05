<script lang="ts">
  import { onMount } from "svelte";
  import PageHeader from "../lib/components/PageHeader.svelte";
  import PageBody from "../lib/components/PageBody.svelte";
  import ContextBar from "../lib/components/ContextBar.svelte";
  import Card from "../lib/components/Card.svelte";
  import NotYetModelled from "../lib/components/NotYetModelled.svelte";
  import LottieLoader from "../lib/components/LottieLoader.svelte";
  import StatementTable, {
    type StatementColumn,
  } from "../lib/components/StatementTable.svelte";
  import { vdtStore, loadVdtScope } from "../lib/data/vdt-store.svelte";
  import { getNode, buildDisplayRows } from "../lib/data/gl-client";
  import {
    periodStore,
    loadPeriods,
    periodYearOf,
  } from "../lib/data/period-store.svelte";
  import { periodState } from "../lib/state/period.svelte";
  import { scopeState } from "../lib/state/scope.svelte";
  import {
    cumulative,
    hierarchyMoneyValues,
    moneyCaption,
    months,
    resolveMoneyScale,
    type MoneyScaleChoice,
  } from "../lib/data/format";
  import type { DisplayRow } from "../lib/data/types";

  // Same fixed pilot scope as VDT Comparison/Reconciliation (V201000000, SOC
  // Crew Cost) — no node picker exists for the VDT hierarchy yet (docs/adr/0037).
  const SOC_CREW_COST = "V201000000";

  let ytdView = $state(false);
  let moneyScale = $state<MoneyScaleChoice>("auto");
  // No monthlyBudget field exists on HierarchyNode yet — Budget is a real,
  // selectable option, but every cell renders the table's existing
  // "not comparable" dash (see docs/adr/0039) until the backend adds it.
  let scenario = $state<"actual" | "budget">("actual");
  let showGlCode = $state(false);

  onMount(loadPeriods);

  // vdtStore isn't populated by App.svelte's app-wide onMount (that's
  // glStore/Accounting only) — this is the VDT hierarchy's own landing page,
  // so it lazily triggers its own fetch, same pattern Comparison/Reconciliation use.
  onMount(() => {
    if (vdtStore.status !== "ready")
      loadVdtScope(scopeState.code, periodState.code);
  });

  const currentYearId = $derived(periodYearOf(periodState.code));
  const monthPeriodCodes = $derived(
    Object.values(periodStore.tree)
      .filter(
        (p) =>
          p.periodType === "Month" && p.id.startsWith(`${currentYearId}-M`),
      )
      .sort((a, b) => a.order - b.order)
      .map((p) => p.id),
  );

  const columns = $derived<StatementColumn[]>(
    monthPeriodCodes.map((code, i) => ({ key: code, label: months[i] })),
  );

  const pnlRows = $derived(buildDisplayRows(vdtStore.tree, SOC_CREW_COST));

  const moneyValues = $derived(hierarchyMoneyValues(vdtStore.tree, SOC_CREW_COST));
  const resolvedMoneyScale = $derived(resolveMoneyScale(moneyScale, moneyValues));
  const currency = $derived(vdtStore.meta?.currency ?? "");

  function cellValue(
    row: DisplayRow,
    _column: StatementColumn,
    index: number,
  ): number | null {
    if (scenario === "budget") return null;
    const monthly = getNode(vdtStore.tree, row.nodeId)?.monthlyActual ?? [];
    if (ytdView && row.kind !== "operational") {
      return cumulative(monthly)[index] ?? 0;
    }
    return monthly[index] ?? 0;
  }

  function rowExists(row: DisplayRow): boolean {
    return (
      row.kind === "operational" ||
      getNode(vdtStore.tree, row.nodeId) !== undefined
    );
  }

  function cellHref(
    row: DisplayRow,
    _column: StatementColumn,
    index: number,
  ): { href: string; title: string } | undefined {
    const periodCode = monthPeriodCodes[index];
    if (!periodCode) return undefined;
    return {
      href: `/vdt/${row.nodeId}?period=${periodCode}`,
      title: `Explore ${months[index]}`,
    };
  }

  function displayLabel(row: DisplayRow): string {
    return showGlCode ? `${row.nodeId} ${row.label}` : row.label;
  }
</script>

<PageHeader title="VDT Trends" />
<PageBody>
  <ContextBar
    showPeriod
    periodYearOnly
    showScenario
    bind:scenario
    showYtd
    bind:ytd={ytdView}
    showComparisonChip={false}
    showMoneyScale
    {currency}
    {moneyValues}
    bind:moneyScale
  />

  {#if vdtStore.status === "loading"}
    <div class="pt-4 flex-1 min-w-0 flex flex-col items-center justify-center gap-2">
      <LottieLoader size={480} />
      <div class="text-lg text-gray-500 dark:text-gray-400">Loading…</div>
    </div>
  {:else if vdtStore.status === "not-yet-modelled"}
    <div class="pt-4 flex-1 min-w-0 flex">
      <NotYetModelled
        label="No VDT data modelled for the selected company yet."
        class="flex-1 flex flex-col items-center justify-center"
      />
    </div>
  {:else}
    <div class="pt-4 min-w-0">
      <Card>
        {#snippet header()}
          <div class="flex justify-between items-baseline mb-2">
            <div class="font-bold text-sm text-gray-900 dark:text-gray-50">
              SOC Crew Cost (VDT)
            </div>
            <div class="flex items-center gap-3">
              <label
                class="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400 cursor-pointer select-none"
              >
                <input
                  type="checkbox"
                  bind:checked={showGlCode}
                  class="h-3 w-3"
                />
                Show code
              </label>
              <div class="text-xs text-gray-500 dark:text-gray-400">
                {moneyCaption(currency, resolvedMoneyScale)}
              </div>
            </div>
          </div>
        {/snippet}
        <StatementTable
          rows={pnlRows}
          {columns}
          {cellValue}
          {rowExists}
          {cellHref}
          labelFor={displayLabel}
          showLabelTooltip
          resizable
          initialLineItemWidth={280}
          lineItemMinWidth={160}
          lineItemMaxWidth={640}
          columnMinWidthPx={64}
          minTableWidthPx={1080}
          {currency}
          moneyScale={resolvedMoneyScale}
        />
      </Card>
    </div>
  {/if}
</PageBody>
