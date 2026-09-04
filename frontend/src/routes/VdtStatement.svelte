<script lang="ts">
  import { onMount } from "svelte";
  import PageHeader from "../lib/components/PageHeader.svelte";
  import PageBody from "../lib/components/PageBody.svelte";
  import ContextBar from "../lib/components/ContextBar.svelte";
  import Card from "../lib/components/Card.svelte";
  import ProfitBridge from "../lib/components/ProfitBridge.svelte";
  import NotYetModelled from "../lib/components/NotYetModelled.svelte";
  import MovementNarration from "../lib/components/MovementNarration.svelte";
  import LottieLoader from "../lib/components/LottieLoader.svelte";
  import StatementTable, {
    type StatementColumn,
  } from "../lib/components/StatementTable.svelte";
  import { vdtStore, loadVdtScope } from "../lib/data/vdt-store.svelte";
  import {
    vdtComparisonStore,
    loadVdtComparison,
  } from "../lib/data/vdt-comparison-store.svelte";
  import {
    narrationStore,
    generateNarration,
  } from "../lib/data/narration-store.svelte";
  import {
    getNode,
    getChildren,
    buildDisplayRows,
  } from "../lib/data/gl-client";
  import {
    getComparisonNode,
    getComparisonChildren,
    buildComparisonRows,
  } from "../lib/data/comparison-client";
  import {
    periodStore,
    loadPeriods,
    periodYearOf,
    periodLabel,
    priorYearSibling,
  } from "../lib/data/period-store.svelte";
  import { periodState } from "../lib/state/period.svelte";
  import { scopeState } from "../lib/state/scope.svelte";
  import {
    comparisonMoneyValues,
    cumulative,
    hierarchyMoneyValues,
    moneyCaption,
    months,
    resolveMoneyScale,
    type MoneyScaleChoice,
  } from "../lib/data/format";
  import type { DisplayRow, Direction, BridgeStep } from "../lib/data/types";

  const SOC_CREW_COST = "V201000000";

  // Defaults on for "vs This Year" (the page's own default comparison mode) —
  // a single month-over-month step is rarely the interesting comparison for
  // a cost line, cumulative-to-date is.
  let ytdView = $state(true);

  onMount(loadPeriods);

  // vdtStore isn't populated by App.svelte's app-wide onMount (that's
  // glStore/Accounting only) — this is the VDT hierarchy's own landing page,
  // so it lazily triggers its own fetch, same pattern VdtTree/VdtRanked use.
  onMount(() => {
    if (vdtStore.status !== "ready")
      loadVdtScope(scopeState.code, periodState.code);
  });

  // Same "always show the whole fiscal year, ignore the Period chip's own
  // month/quarter granularity" behaviour as Trends (see docs/adr/0026) —
  // this is the VDT hierarchy's equivalent full-statement landing, not a
  // scoped drill-down view (that's Ranked/Tree below root).
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
  const visibleMonthIndices = $derived(monthPeriodCodes.map((_, i) => i));

  // --- vs This Year / vs Last Year comparison (see docs/adr/0034) ---
  let vdtComparisonMode = $state("vs This Year");
  // Higher default than FinancialComparison's 0.7 — SOC Crew Cost's
  // month-over-month swings run much smaller relative to its total
  // (~1%, vs P&L-level comparisons) so the delta bars need more of the
  // chart's height to read as anything but a sliver against the total bars.
  let bridgeEmphasis = $state(0.9);
  let vdtPeriodA = $state<string | undefined>(undefined);
  let vdtPeriodB = $state<string | undefined>(undefined);
  const isComparisonMode = $derived(
    vdtComparisonMode === "vs This Year" ||
      vdtComparisonMode === "vs Last Year",
  );
  let moneyScale = $state<MoneyScaleChoice>("auto");

  // "vs Last Year" only exposes one picker (the "this year" side) — its pair
  // is derived automatically, same month one fiscal year back.
  const resolvedPeriodA = $derived(
    vdtComparisonMode === "vs Last Year"
      ? vdtPeriodA
        ? priorYearSibling(vdtPeriodA)
        : undefined
      : vdtPeriodA,
  );
  const resolvedPeriodB = $derived(
    vdtComparisonMode === "vs Last Year" ? vdtPeriodA : vdtPeriodB,
  );

  // Default both pickers to the current real-world month once the current
  // year's Month periods have loaded — "vs This Year" defaults to the two
  // most recent months, "vs Last Year" to the current month (see docs/adr/0034).
  $effect(() => {
    if (vdtPeriodA !== undefined || monthPeriodCodes.length < 12) return;
    const currentMonthIndex = new Date().getMonth();
    vdtPeriodA = monthPeriodCodes[Math.max(0, currentMonthIndex - 1)];
    vdtPeriodB = monthPeriodCodes[currentMonthIndex];
  });

  $effect(() => {
    if (!isComparisonMode || !resolvedPeriodA || !resolvedPeriodB) return;
    loadVdtComparison(
      scopeState.code,
      SOC_CREW_COST,
      resolvedPeriodA,
      resolvedPeriodB,
      ytdView,
    );
    narrationStore.reset();
  });

  function handleExplainMovement(): void {
    if (!resolvedPeriodA || !resolvedPeriodB) return;
    generateNarration(
      scopeState.code,
      SOC_CREW_COST,
      resolvedPeriodA,
      resolvedPeriodB,
      ytdView,
    );
  }

  const comparisonRoot = $derived(
    getComparisonNode(vdtComparisonStore.tree, SOC_CREW_COST),
  );
  const moneyValues = $derived(
    isComparisonMode
      ? comparisonMoneyValues(vdtComparisonStore.tree, SOC_CREW_COST)
      : hierarchyMoneyValues(vdtStore.tree, SOC_CREW_COST),
  );
  const resolvedMoneyScale = $derived(
    resolveMoneyScale(moneyScale, moneyValues),
  );
  const currency = $derived(
    vdtComparisonStore.meta?.currency ?? vdtStore.meta?.currency ?? "",
  );

  let lastComparisonScaleKey = "";
  $effect(() => {
    const key = `${vdtComparisonMode}:${resolvedPeriodA ?? ""}:${resolvedPeriodB ?? ""}:${ytdView}`;
    if (lastComparisonScaleKey && key !== lastComparisonScaleKey)
      moneyScale = "auto";
    lastComparisonScaleKey = key;
  });

  function bridgeKind(direction: Direction): BridgeStep["kind"] {
    return direction === "favourable"
      ? "increase"
      : direction === "adverse"
        ? "decrease"
        : "neutral";
  }

  // SOC Crew Cost is a cost — actual/valueA/valueB are negative by sign
  // convention (docs/adr/0023), so a literal signed waterfall would grow
  // downward from zero. That reads as upside-down to a finance user (a cost
  // *increase* should grow the bar, not shrink it toward zero) — so the
  // chart displays magnitude (sign-flipped when the root is a cost), while
  // color still tracks favourable/adverse off the real signed direction
  // (see docs/adr/0034), not the flipped display value.
  const bridgeFlip = $derived(
    comparisonRoot && comparisonRoot.valueA < 0 ? -1 : 1,
  );

  const comparisonBridgeSteps = $derived<BridgeStep[]>(
    comparisonRoot
      ? [
          {
            label: periodLabel(resolvedPeriodA ?? ""),
            value: comparisonRoot.valueA * bridgeFlip,
            kind: "total",
          },
          ...getComparisonChildren(vdtComparisonStore.tree, comparisonRoot)
            .filter(
              (c) => c.nodeType !== "Driver Formula" && c.nodeType !== "Driver",
            )
            .map((c) => ({
              label: c.name,
              value: c.delta * bridgeFlip,
              kind: bridgeKind(c.direction),
            })),
          {
            label: periodLabel(resolvedPeriodB ?? ""),
            value: comparisonRoot.valueB * bridgeFlip,
            kind: "total" as const,
          },
        ]
      : [],
  );

  const comparisonRows = $derived(
    buildComparisonRows(vdtComparisonStore.tree, SOC_CREW_COST),
  );

  const comparisonColumns = $derived<StatementColumn[]>([
    { key: "A", label: periodLabel(resolvedPeriodA ?? "") },
    { key: "B", label: periodLabel(resolvedPeriodB ?? "") },
    { key: "delta", label: "Δ", isDelta: true },
  ]);

  function comparisonCellValue(
    row: DisplayRow,
    column: StatementColumn,
  ): number {
    const node = getComparisonNode(vdtComparisonStore.tree, row.nodeId);
    if (!node) return 0;
    if (column.key === "A") return node.valueA;
    if (column.key === "B") return node.valueB;
    return node.delta;
  }

  function comparisonCellDirection(row: DisplayRow): Direction {
    return (
      getComparisonNode(vdtComparisonStore.tree, row.nodeId)?.direction ??
      "neutral"
    );
  }

  function comparisonCellDeltaPct(row: DisplayRow): number | null {
    return (
      getComparisonNode(vdtComparisonStore.tree, row.nodeId)?.deltaPct ?? null
    );
  }

  function comparisonRowExists(row: DisplayRow): boolean {
    return getComparisonNode(vdtComparisonStore.tree, row.nodeId) !== undefined;
  }

  let showGlCode = $state(false);
  function displayLabel(row: DisplayRow): string {
    return showGlCode ? `${row.nodeId} ${row.label}` : row.label;
  }

  const pnlRows = $derived(buildDisplayRows(vdtStore.tree, "V201000000"));

  const columns = $derived<StatementColumn[]>(
    visibleMonthIndices.map((i, idx) => ({
      key: monthPeriodCodes[i] ?? `pending-${idx}`,
      label: months[i],
    })),
  );

  function monthlyValuesFor(nodeId: string): number[] {
    const monthlyActual = getNode(vdtStore.tree, nodeId)?.monthlyActual ?? [];
    return visibleMonthIndices.map((i) => monthlyActual[i] ?? 0);
  }

  function cellValue(
    row: DisplayRow,
    _column: StatementColumn,
    index: number,
  ): number {
    const monthly = monthlyValuesFor(row.nodeId);
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
    const periodCode = monthPeriodCodes[visibleMonthIndices[index]];
    if (!periodCode) return undefined;
    const month = months[visibleMonthIndices[index]];
    return {
      href: `/vdt/${row.nodeId}?period=${periodCode}`,
      title: `Explore ${month}`,
    };
  }

  // Default bridge scope: SOC Crew Cost (V201000000, under Cost of Revenue —
  // see docs/vdt-hierarchy-crew-cost.csv), decomposed into its direct
  // Activity Node children.
  const socCrewCost = $derived(getNode(vdtStore.tree, "V201000000"));
  const socCrewCostChildren = $derived(
    socCrewCost ? getChildren(vdtStore.tree, socCrewCost) : [],
  );

  // Same magnitude flip as comparisonBridgeSteps — SOC Crew Cost's actual is
  // negative (a cost), and a literal signed bridge would grow downward.
  const singlePeriodFlip = $derived(
    socCrewCost && socCrewCost.actual < 0 ? -1 : 1,
  );

  const profitBridgeSteps = $derived(
    socCrewCost && socCrewCostChildren.length
      ? [
          ...socCrewCostChildren.map((child) => ({
            label: child.name,
            value: child.actual * singlePeriodFlip,
            kind: "decrease" as const,
          })),
          {
            label: socCrewCost.name,
            value: socCrewCost.actual * singlePeriodFlip,
            kind: "total" as const,
          },
        ]
      : [],
  );
</script>

<PageHeader title="Value Driver" />
<PageBody>
  <ContextBar
    showYtd
    showPeriod={false}
    bind:ytd={ytdView}
    vdtComparison
    bind:vdtComparisonMode
    bind:vdtPeriodA
    bind:vdtPeriodB
    showMoneyScale
    {currency}
    {moneyValues}
    bind:moneyScale
  />

  {#if isComparisonMode}
    {#if !resolvedPeriodA || !resolvedPeriodB}
      <div class="pt-4 text-sm text-gray-500 dark:text-gray-400">
        Pick a period to compare.
      </div>
    {:else if vdtComparisonStore.status === "loading"}
      <div class="pt-4 flex-1 min-w-0 flex flex-col items-center justify-center gap-2">
        <LottieLoader size={480} />
        <div class="text-lg text-gray-500 dark:text-gray-400">Loading…</div>
      </div>
    {:else if vdtComparisonStore.status === "not-yet-modelled"}
      <div class="pt-4 flex-1 min-w-0 flex">
        <NotYetModelled
          label="No VDT data modelled for the selected company yet."
          class="flex-1 flex flex-col items-center justify-center"
        />
      </div>
    {:else if comparisonRoot}
      <div class="flex flex-col gap-4 pt-4 min-w-0 lg:flex-row">
        <div class="flex flex-col gap-4 min-w-0 flex-1">
          <Card>
            {#snippet header()}
              <div
                class="flex flex-wrap items-center justify-between gap-3 mb-2"
              >
                <div class="font-bold text-sm text-gray-900 dark:text-gray-50">
                  SOC Crew Cost: {periodLabel(resolvedPeriodA ?? "")} → {periodLabel(
                    resolvedPeriodB ?? "",
                  )}
                </div>
                <label
                  class="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400 select-none"
                >
                  Emphasize changes
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    bind:value={bridgeEmphasis}
                    class="accent-indigo-600 dark:accent-indigo-400"
                  />
                </label>
              </div>
            {/snippet}
            <ProfitBridge
              steps={comparisonBridgeSteps}
              height={300}
              emphasis={bridgeEmphasis}
              {currency}
              moneyScale={resolvedMoneyScale}
            />
          </Card>

          <Card>
            {#snippet header()}
              <div class="flex justify-between items-baseline mb-2">
                <div class="font-bold text-sm text-gray-900 dark:text-gray-50">
                  SOC Crew Cost (VDT)
                </div>
                <div class="text-xs text-gray-500 dark:text-gray-400">
                  {moneyCaption(currency, resolvedMoneyScale)}
                </div>
              </div>
            {/snippet}
            <StatementTable
              rows={comparisonRows}
              columns={comparisonColumns}
              cellValue={comparisonCellValue}
              rowExists={comparisonRowExists}
              cellDirection={comparisonCellDirection}
              cellDeltaPct={comparisonCellDeltaPct}
              showDeltaColoring
              showLabelTooltip
              resizable
              initialLineItemWidth={280}
              lineItemMinWidth={160}
              lineItemMaxWidth={640}
              columnMinWidthPx={110}
              minTableWidthPx={640}
              resetKey={SOC_CREW_COST}
              {currency}
              moneyScale={resolvedMoneyScale}
            />
          </Card>
        </div>

        <div class="lg:w-80 shrink-0">
          <Card>
            <MovementNarration
              status={narrationStore.status}
              narration={narrationStore.narration}
              error={narrationStore.error}
              onGenerate={handleExplainMovement}
              {currency}
              moneyScale={resolvedMoneyScale}
            />
          </Card>
        </div>
      </div>
    {/if}
  {:else if vdtStore.status === "loading"}
    <div class="pt-4 flex-1 min-w-0 flex flex-col items-center justify-center gap-2">
      <LottieLoader size={160} />
      <div class="text-sm text-gray-500 dark:text-gray-400">Loading…</div>
    </div>
  {:else if vdtStore.status === "not-yet-modelled"}
    <div class="pt-4 flex-1 min-w-0 flex">
      <NotYetModelled
        label="No VDT data modelled for the selected company yet."
        class="flex-1 flex flex-col items-center justify-center"
      />
    </div>
  {:else}
    <div class="flex flex-col gap-4 pt-4 min-w-0">
      <Card title="Cost Bridge: SOC Crew Cost">
        <ProfitBridge
          steps={profitBridgeSteps}
          height={300}
          {currency}
          moneyScale={resolvedMoneyScale}
        />
      </Card>

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
