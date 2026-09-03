<script lang="ts">
  import { onMount } from "svelte";
  import PageHeader from "../lib/components/PageHeader.svelte";
  import PageBody from "../lib/components/PageBody.svelte";
  import ContextBar from "../lib/components/ContextBar.svelte";
  import Card from "../lib/components/Card.svelte";
  import KpiCard from "../lib/components/KpiCard.svelte";
  import MonthlyTrendChart from "../lib/components/MonthlyTrendChart.svelte";
  import ProfitBridge from "../lib/components/ProfitBridge.svelte";
  import NotYetModelled from "../lib/components/NotYetModelled.svelte";
  import StatementTable, {
    type StatementColumn,
  } from "../lib/components/StatementTable.svelte";
  import { vdtStore, loadVdtScope } from "../lib/data/vdt-store.svelte";
  import { getNode, buildDisplayRows } from "../lib/data/gl-client";
  import { periodStore, loadPeriods, periodYearOf } from "../lib/data/period-store.svelte";
  import { periodState } from "../lib/state/period.svelte";
  import { scopeState } from "../lib/state/scope.svelte";
  import { months, formatRmAuto, cumulative } from "../lib/data/format";
  import type { DisplayRow } from "../lib/data/types";

  let ytdView = $state(false);

  onMount(loadPeriods);

  // vdtStore isn't populated by App.svelte's app-wide onMount (that's
  // glStore/Accounting only) — this is the VDT hierarchy's own landing page,
  // so it lazily triggers its own fetch, same pattern VdtTree/VdtRanked use.
  onMount(() => {
    if (vdtStore.status !== "ready") loadVdtScope(scopeState.code, periodState.code);
  });

  // Same "always show the whole fiscal year, ignore the Period chip's own
  // month/quarter granularity" behaviour as Trends (see docs/adr/0026) —
  // this is the VDT hierarchy's equivalent full-statement landing, not a
  // scoped drill-down view (that's Ranked/Tree below root).
  const currentYearId = $derived(periodYearOf(periodState.code));
  const monthPeriodCodes = $derived(
    Object.values(periodStore.tree)
      .filter((p) => p.periodType === "Month" && p.id.startsWith(`${currentYearId}-M`))
      .sort((a, b) => a.order - b.order)
      .map((p) => p.id),
  );
  const visibleMonthIndices = $derived(monthPeriodCodes.map((_, i) => i));

  let showGlCode = $state(false);
  function displayLabel(row: DisplayRow): string {
    return showGlCode ? `${row.nodeId} ${row.label}` : row.label;
  }

  const pnlRows = $derived(buildDisplayRows(vdtStore.tree));

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

  function cellValue(row: DisplayRow, _column: StatementColumn, index: number): number {
    const monthly = monthlyValuesFor(row.nodeId);
    if (ytdView && row.kind !== "operational") {
      return cumulative(monthly)[index] ?? 0;
    }
    return monthly[index] ?? 0;
  }

  function rowExists(row: DisplayRow): boolean {
    return row.kind === "operational" || getNode(vdtStore.tree, row.nodeId) !== undefined;
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

  // Same level-1-under-NPAT codes as Trends — shared verbatim outside the
  // Cost of Revenue/Revenue pilot scope, and Revenue/Cost of Revenue
  // themselves resolve fine here too (VDT just has different children
  // beneath them where an Activity Node has been seeded — see docs/adr/0033).
  const revenue = $derived(getNode(vdtStore.tree, "PNL-0002"));
  const costOfRevenue = $derived(getNode(vdtStore.tree, "PNL-0011"));
  const grossProfit = $derived(getNode(vdtStore.tree, "PNL-0001"));
  const gaExpenses = $derived(getNode(vdtStore.tree, "PNL-0030"));
  const otherIncomeExpenses = $derived(getNode(vdtStore.tree, "PNL-0054"));
  const secondaryCost = $derived(getNode(vdtStore.tree, "PNL-0086"));
  const taxation = $derived(getNode(vdtStore.tree, "PNL-0087"));
  const npat = $derived(getNode(vdtStore.tree, "NPAT"));

  function scoped(monthlyActual: number[]): number[] {
    return visibleMonthIndices.map((i) => monthlyActual[i] ?? 0);
  }

  function trailing24(
    node: { monthlyActual: number[]; monthlyPriorYear: number[] },
    abs = false,
  ): { trend: number[]; tooltips: string[] } {
    const transform = abs ? Math.abs : (v: number) => v;
    const monthLabels = visibleMonthIndices.map((i) => months[i]);
    const trend = [
      ...scoped(node.monthlyPriorYear).map(transform),
      ...scoped(node.monthlyActual).map(transform),
    ];
    const tooltips = trend.map((v, i) => {
      const year = i < monthLabels.length ? "Prior Year" : "This Year";
      const month = monthLabels[i % monthLabels.length];
      return `${month} (${year}): ${formatRmAuto(v)}`;
    });
    return { trend, tooltips };
  }

  const revenueTrend = $derived(revenue && trailing24(revenue));
  const costOfRevenueTrend = $derived(costOfRevenue && trailing24(costOfRevenue, true));
  const grossProfitTrend = $derived(grossProfit && trailing24(grossProfit));
  const npatTrend = $derived(npat && trailing24(npat));

  const vdtKpis = $derived(
    revenue && costOfRevenue && grossProfit && npat && revenueTrend && costOfRevenueTrend && grossProfitTrend && npatTrend
      ? [
          {
            id: "vdt-revenue-ytd",
            label: "Revenue",
            value: formatRmAuto(revenue.actual),
            trend: revenueTrend.trend,
            trendTooltips: revenueTrend.tooltips,
            trendFillClass: "fill-gray-900 dark:fill-gray-50",
          },
          {
            id: "vdt-cost-of-revenue-ytd",
            label: "Cost of Revenue",
            value: formatRmAuto(Math.abs(costOfRevenue.actual)),
            trend: costOfRevenueTrend.trend,
            trendTooltips: costOfRevenueTrend.tooltips,
            trendFillClass: "fill-red-600 dark:fill-red-400",
          },
          {
            id: "vdt-gross-profit-ytd",
            label: "Gross Profit",
            value: formatRmAuto(grossProfit.actual),
            trend: grossProfitTrend.trend,
            trendTooltips: grossProfitTrend.tooltips,
            trendFillClass: "fill-emerald-600 dark:fill-emerald-400",
          },
          {
            id: "vdt-npat-ytd",
            label: "NPAT",
            value: formatRmAuto(npat.actual),
            trend: npatTrend.trend,
            trendTooltips: npatTrend.tooltips,
            trendFillClass: "fill-blue-600 dark:fill-blue-400",
          },
        ]
      : [],
  );

  const monthlyPerformanceChart = $derived(
    revenue && costOfRevenue && grossProfit && npat
      ? [
          { label: "Revenue", values: scoped(revenue.monthlyActual) },
          { label: "COR", values: scoped(costOfRevenue.monthlyActual).map(Math.abs) },
          { label: "GP", values: scoped(grossProfit.monthlyActual) },
          { label: "NPAT", values: scoped(npat.monthlyActual) },
        ]
      : [],
  );
  const visibleMonthLabels = $derived(visibleMonthIndices.map((i) => months[i]));

  const profitBridgeSteps = $derived(
    revenue &&
      costOfRevenue &&
      grossProfit &&
      gaExpenses &&
      otherIncomeExpenses &&
      secondaryCost &&
      taxation &&
      npat
      ? [
          { label: "Revenue", value: revenue.actual, kind: "total" as const },
          { label: "Cost of Revenue", value: costOfRevenue.actual, kind: "decrease" as const },
          { label: "Gross Profit", value: grossProfit.actual, kind: "total" as const },
          { label: "G&A Expenses", value: gaExpenses.actual, kind: "decrease" as const },
          { label: "Other Income & Expenses", value: otherIncomeExpenses.actual, kind: "decrease" as const },
          { label: "Secondary Cost Elements", value: secondaryCost.actual, kind: "decrease" as const },
          { label: "Taxation", value: taxation.actual, kind: "decrease" as const },
          { label: "NPAT", value: npat.actual, kind: "total" as const },
        ]
      : [],
  );
</script>

<PageHeader title="Value Driver" />
<PageBody>
  <ContextBar showYtd showPeriod={false} bind:ytd={ytdView} />

  {#if vdtStore.status === "loading"}
    <div class="pt-4 flex-1 min-w-0 flex items-center justify-center">Loading…</div>
  {:else if vdtStore.status === "not-yet-modelled"}
    <div class="pt-4 flex-1 min-w-0 flex">
      <NotYetModelled
        label="No VDT data modelled for the selected company/BU yet."
        class="flex-1 flex flex-col items-center justify-center"
      />
    </div>
  {:else}
    <div class="flex flex-col gap-4 pt-4 min-w-0">
      <div class="grid grid-cols-4 max-[900px]:grid-cols-2 gap-2.5">
        {#each vdtKpis as kpi (kpi.id)}
          <KpiCard {kpi} />
        {/each}
      </div>

      <div class="flex max-[900px]:flex-col gap-4">
        <Card class="flex-1 min-w-0" title="Income Statement Key Items">
          <MonthlyTrendChart series={monthlyPerformanceChart} months={visibleMonthLabels} />
        </Card>

        <Card class="flex-1 min-w-0" title="Profit Bridge: Revenue to NPAT">
          <ProfitBridge steps={profitBridgeSteps} height={300} />
        </Card>
      </div>

      <Card>
        {#snippet header()}
          <div class="flex justify-between items-baseline mb-2">
            <div class="font-bold text-sm text-gray-900 dark:text-gray-50">
              Income Statement (VDT)
            </div>
            <div class="flex items-center gap-3">
              <label
                class="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400 cursor-pointer select-none"
              >
                <input type="checkbox" bind:checked={showGlCode} class="h-3 w-3" />
                Show code
              </label>
              <div class="text-xs text-gray-500 dark:text-gray-400">RM millions</div>
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
        />
      </Card>
    </div>
  {/if}
</PageBody>
