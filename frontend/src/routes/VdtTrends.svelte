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
  import TrendAnalysis from "../lib/components/TrendAnalysis.svelte";
  import {
    trendAnalysisStore,
    generateTrendAnalysis,
  } from "../lib/data/trend-analysis-store.svelte";
  import { vdtStore, loadVdtScope } from "../lib/data/vdt-store.svelte";
  import { getNode, buildDisplayRows } from "../lib/data/gl-client";
  import {
    periodStore,
    loadPeriods,
    periodYearOf,
    trailingWindowMonths,
    calendarMonthLabel,
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

  // Same fixed pilot scope as VDT Variance Analysis/Reconciliation (V201000000, SOC
  // Crew Cost) — no node picker exists for the VDT hierarchy yet (docs/adr/0037).
  const SOC_CREW_COST = "V201000000";

  let ytdView = $state(false);
  let moneyScale = $state<MoneyScaleChoice>("auto");
  // No monthlyBudget field exists on HierarchyNode yet — Budget is a real,
  // selectable option, but every cell renders the table's existing
  // "not comparable" dash (see docs/adr/0039) until the backend adds it.
  let source = $state<"actual" | "budget">("actual");
  let showGlCode = $state(false);

  // Financial Year (existing, default) vs Trailing (new) — see docs/adr/0042.
  let trendsMode = $state<"financial-year" | "trailing">("financial-year");
  let trailingAnchor = $state<string | undefined>(undefined);

  onMount(loadPeriods);

  // Trailing mode's default anchor is the latest month of the latest fiscal
  // year (see docs/adr/0042) — set once periods load, and only if the user
  // hasn't already picked one, so this never overwrites a live selection.
  const latestYearId = $derived(
    Object.values(periodStore.tree)
      .filter((p) => p.periodType === "Year")
      .sort((a, b) => b.order - a.order)[0]?.id,
  );
  const latestYearLastMonth = $derived(
    latestYearId
      ? Object.values(periodStore.tree)
          .filter((p) => p.periodType === "Month" && p.id.startsWith(`${latestYearId}-M`))
          .sort((a, b) => b.order - a.order)[0]?.id
      : undefined,
  );
  $effect(() => {
    if (!trailingAnchor && latestYearLastMonth) trailingAnchor = latestYearLastMonth;
  });

  const currentYearId = $derived(periodYearOf(periodState.code));
  const monthPeriodCodes = $derived(
    trendsMode === "trailing"
      ? trailingAnchor
        ? trailingWindowMonths(trailingAnchor)
        : []
      : Object.values(periodStore.tree)
          .filter(
            (p) =>
              p.periodType === "Month" && p.id.startsWith(`${currentYearId}-M`),
          )
          .sort((a, b) => a.order - b.order)
          .map((p) => p.id),
  );

  const columns = $derived<StatementColumn[]>(
    trendsMode === "trailing"
      ? monthPeriodCodes.map((code) => ({ key: code, label: calendarMonthLabel(code) }))
      : monthPeriodCodes.map((code, i) => ({ key: code, label: months[i] })),
  );

  // vdtStore isn't populated by App.svelte's app-wide onMount (that's
  // glStore/Accounting only) — this is the VDT hierarchy's own landing page,
  // so it owns its own fetch, reactively keyed on whatever currently
  // determines the window (Company + mode + Financial Year/Trailing anchor).
  // Trailing mode's anchor applies live (no Apply-button staging, unlike
  // Business/Period — see docs/adr/0042), so this effect is this screen's
  // sole source of truth for when to refetch, replacing the old
  // mount-only/status-guarded fetch.
  let lastFetchKey = "";
  $effect(() => {
    const anchor = trendsMode === "trailing" ? trailingAnchor : currentYearId;
    if (!anchor) return;
    const key = `${scopeState.code}:${trendsMode}:${anchor}`;
    if (key === lastFetchKey) return;
    const isFirstRun = lastFetchKey === "";
    lastFetchKey = key;
    // On mount, skip the fetch if vdtStore already holds data (e.g. arriving
    // from another VDT route within the same session) — mirrors the
    // previous onMount status guard, avoiding an unconditional refetch/
    // loading flicker on every visit. Any later change always refetches.
    if (isFirstRun && vdtStore.status === "ready") return;
    if (trendsMode === "trailing") {
      loadVdtScope(scopeState.code, undefined, anchor);
    } else {
      loadVdtScope(scopeState.code, anchor);
    }
  });

  const pnlRows = $derived(buildDisplayRows(vdtStore.tree, SOC_CREW_COST));

  const moneyValues = $derived(hierarchyMoneyValues(vdtStore.tree, SOC_CREW_COST));
  const resolvedMoneyScale = $derived(resolveMoneyScale(moneyScale, moneyValues));
  const currency = $derived(vdtStore.meta?.currency ?? "");

  function cellValue(
    row: DisplayRow,
    _column: StatementColumn,
    index: number,
  ): number | null {
    if (source === "budget") return null;
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
    const label = trendsMode === "trailing" ? calendarMonthLabel(periodCode) : months[index];
    return {
      href: `/vdt/${row.nodeId}?period=${periodCode}`,
      title: `Explore ${label}`,
    };
  }

  function displayLabel(row: DisplayRow): string {
    return showGlCode ? `${row.nodeId} ${row.label}` : row.label;
  }

  function handleAnalyseTrends(): void {
    if (trendsMode === "trailing") {
      if (!trailingAnchor) return;
      generateTrendAnalysis(scopeState.code, source, { trailingEnd: trailingAnchor });
    } else {
      if (!currentYearId) return;
      generateTrendAnalysis(scopeState.code, source, { year: currentYearId });
    }
  }

  // Reset when the underlying data Trend Analysis reads changes: Company,
  // window (Year, or Trailing mode + anchor), or Actual/Budget. GL-code
  // toggle, Monetary scale, and Cumulative do NOT reset — none change the
  // monthly series (docs/adr/0040, docs/adr/0042).
  let lastTrendKey = "";
  $effect(() => {
    const anchor = trendsMode === "trailing" ? trailingAnchor : currentYearId;
    const key = `${scopeState.code}:${trendsMode}:${anchor}:${source}`;
    if (lastTrendKey && key !== lastTrendKey) trendAnalysisStore.reset();
    lastTrendKey = key;
  });
</script>

<PageHeader title="VDT Trends" />
<PageBody>
  <ContextBar
    showPeriod
    periodYearOnly
    showTrendsMode
    bind:trendsMode
    bind:trailingAnchor
    showSource
    bind:source
    showYtd
    ytdLabel="Cumulative"
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
      <div>
        <Card>
          <TrendAnalysis
            status={trendAnalysisStore.status}
            analysis={trendAnalysisStore.analysis}
            error={trendAnalysisStore.error}
            onGenerate={handleAnalyseTrends}
            {currency}
            moneyScale={resolvedMoneyScale}
            months={trendsMode === "trailing" ? monthPeriodCodes.map(calendarMonthLabel) : months}
            idleText={trendsMode === "trailing"
              ? "Scan the trailing window for month-over-month movements worth flagging."
              : "Scan the full fiscal year for month-over-month movements worth flagging."}
            quietText={trendsMode === "trailing"
              ? "Quiet window — nothing crossed the threshold."
              : "Quiet year — nothing crossed the threshold."}
          />
        </Card>
      </div>
      <div class="mt-4">
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
    </div>
  {/if}
</PageBody>
