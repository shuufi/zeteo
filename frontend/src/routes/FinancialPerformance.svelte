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
  import { glStore } from "../lib/data/gl-store.svelte";
  import { getNode, buildDisplayRows } from "../lib/data/gl-client";
  import { periodStore, loadPeriods, periodYearOf } from "../lib/data/period-store.svelte";
  import { periodState } from "../lib/state/period.svelte";
  import {
    cumulative,
    formatMoney,
    hierarchyMoneyValues,
    moneyCaption,
    months,
    resolveMoneyScale,
    type MoneyScaleChoice,
  } from "../lib/data/format";
  import type { DisplayRow } from "../lib/data/types";

  let ytdView = $state(false);
  let moneyScale = $state<MoneyScaleChoice>("auto");
  const moneyValues = $derived(hierarchyMoneyValues(glStore.tree, "NPAT"));
  const resolvedMoneyScale = $derived(resolveMoneyScale(moneyScale, moneyValues));
  const currency = $derived(glStore.meta?.currency ?? "");

  onMount(loadPeriods);

  // Three fiscal years coexist as sibling Year roots now (see docs/adr/0032)
  // — glStore.tree was fetched scoped to whichever year periodState.code
  // belongs to (Financial ignores the chip's own month/quarter granularity,
  // per docs/adr/0026, but not which year the rest of the app is looking
  // at), so that's the one year's 12 months to show here.
  const currentYearId = $derived(periodYearOf(periodState.code));
  const monthPeriodCodes = $derived(
    Object.values(periodStore.tree)
      .filter((p) => p.periodType === "Month" && p.id.startsWith(`${currentYearId}-M`))
      .sort((a, b) => a.order - b.order)
      .map((p) => p.id),
  );

  // Financial always shows the whole fiscal year — unlike VDT
  // Explorer/Driver Diagnostic, it doesn't scope to the Period chip (see
  // docs/adr/0026, reverted from genuinely scoping per follow-up feedback):
  // its Income Statement is a grid of all 12 month columns and its KPI cards
  // summarize the full year, so the chip stays visible/interactive here
  // (picking still affects the other two screens) but this page ignores it.
  const visibleMonthIndices = $derived(monthPeriodCodes.map((_, i) => i));

  // Off by default — the GL code is noise until you need to cross-reference
  // SAP, so it's opt-in via the checkbox next to the table title.
  let showGlCode = $state(false);
  function displayLabel(row: DisplayRow): string {
    return showGlCode ? `${row.nodeId} ${row.label}` : row.label;
  }

  const pnlRows = $derived(buildDisplayRows(glStore.tree));

  // Statement table columns are the fiscal year's 12 months — column key is
  // the real period code when periods have loaded (needed for the drill-down
  // link below), falling back to a stable placeholder otherwise so a column
  // is never keyed `undefined`.
  const columns = $derived<StatementColumn[]>(
    visibleMonthIndices.map((i, idx) => ({
      key: monthPeriodCodes[i] ?? `pending-${idx}`,
      label: months[i],
    })),
  );

  function monthlyValuesFor(nodeId: string): number[] {
    const monthlyActual = getNode(glStore.tree, nodeId)?.monthlyActual ?? [];
    return visibleMonthIndices.map((i) => monthlyActual[i] ?? 0);
  }

  // Cumulative sum is meaningless for rates/percentages/day-counts — operational
  // driver rows always show their monthly (period) value, regardless of the toggle.
  function cellValue(row: DisplayRow, _column: StatementColumn, index: number): number {
    const monthly = monthlyValuesFor(row.nodeId);
    if (ytdView && row.kind !== "operational") {
      return cumulative(monthly)[index] ?? 0;
    }
    return monthly[index] ?? 0;
  }

  function rowExists(row: DisplayRow): boolean {
    return row.kind === "operational" || getNode(glStore.tree, row.nodeId) !== undefined;
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
      title: `Explore ${month} in VDT Explorer`,
    };
  }

  // Level-1 children of NPAT in the real GL/FSI hierarchy — see docs/adr/0022.
  const revenue = $derived(getNode(glStore.tree, "PNL-0002"));
  const costOfRevenue = $derived(getNode(glStore.tree, "PNL-0011"));
  const grossProfit = $derived(getNode(glStore.tree, "PNL-0001"));
  const gaExpenses = $derived(getNode(glStore.tree, "PNL-0030"));
  const otherIncomeExpenses = $derived(getNode(glStore.tree, "PNL-0054"));
  const secondaryCost = $derived(getNode(glStore.tree, "PNL-0086"));
  const taxation = $derived(getNode(glStore.tree, "PNL-0087"));
  const npat = $derived(getNode(glStore.tree, "NPAT"));

  function scoped(monthlyActual: number[]): number[] {
    return visibleMonthIndices.map((i) => monthlyActual[i] ?? 0);
  }

  // Trailing 24 months for the KPI card bar charts — prior year's monthly
  // figures followed by the current year's, in chronological order (see
  // gl_tree.py's monthlyPriorYear, sourced from the prior_year GLFact scenario).
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
      return `${month} (${year}): ${formatMoney(v, currency, resolvedMoneyScale)}`;
    });
    return { trend, tooltips };
  }

  const revenueTrend = $derived(revenue && trailing24(revenue));
  const costOfRevenueTrend = $derived(costOfRevenue && trailing24(costOfRevenue, true));
  const grossProfitTrend = $derived(grossProfit && trailing24(grossProfit));
  const npatTrend = $derived(npat && trailing24(npat));

  const financialKpis = $derived(
    revenue && costOfRevenue && grossProfit && npat && revenueTrend && costOfRevenueTrend && grossProfitTrend && npatTrend
      ? [
          {
            id: "revenue-ytd",
            label: "Revenue",
            value: formatMoney(revenue.actual, currency, resolvedMoneyScale),
            trend: revenueTrend.trend,
            trendTooltips: revenueTrend.tooltips,
            trendFillClass: "fill-gray-900 dark:fill-gray-50",
          },
          {
            id: "cost-of-revenue-ytd",
            label: "Cost of Revenue",
            value: formatMoney(Math.abs(costOfRevenue.actual), currency, resolvedMoneyScale),
            trend: costOfRevenueTrend.trend,
            trendTooltips: costOfRevenueTrend.tooltips,
            trendFillClass: "fill-red-600 dark:fill-red-400",
          },
          {
            id: "gross-profit-ytd",
            label: "Gross Profit",
            value: formatMoney(grossProfit.actual, currency, resolvedMoneyScale),
            trend: grossProfitTrend.trend,
            trendTooltips: grossProfitTrend.tooltips,
            trendFillClass: "fill-emerald-600 dark:fill-emerald-400",
          },
          {
            id: "npat-ytd",
            label: "NPAT",
            value: formatMoney(npat.actual, currency, resolvedMoneyScale),
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
          {
            label: "COR",
            values: scoped(costOfRevenue.monthlyActual).map(Math.abs),
          },
          { label: "GP", values: scoped(grossProfit.monthlyActual) },
          { label: "NPAT", values: scoped(npat.monthlyActual) },
        ]
      : [],
  );
  const visibleMonthLabels = $derived(
    visibleMonthIndices.map((i) => months[i]),
  );

  // Bridge steps map 1:1 onto NPAT's real direct children — no curated ref
  // lists needed, values already carry the right sign (see docs/adr/0023).
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
          {
            label: "Cost of Revenue",
            value: costOfRevenue.actual,
            kind: "decrease" as const,
          },
          {
            label: "Gross Profit",
            value: grossProfit.actual,
            kind: "total" as const,
          },
          {
            label: "G&A Expenses",
            value: gaExpenses.actual,
            kind: "decrease" as const,
          },
          {
            label: "Other Income & Expenses",
            value: otherIncomeExpenses.actual,
            kind: "decrease" as const,
          },
          {
            label: "Secondary Cost Elements",
            value: secondaryCost.actual,
            kind: "decrease" as const,
          },
          {
            label: "Taxation",
            value: taxation.actual,
            kind: "decrease" as const,
          },
          { label: "NPAT", value: npat.actual, kind: "total" as const },
        ]
      : [],
  );
</script>

<PageHeader title="Financial Trends" />
<PageBody>
  <ContextBar showYtd showPeriod={false} bind:ytd={ytdView} showMoneyScale {currency} {moneyValues} bind:moneyScale />

  {#if glStore.status === "loading"}
    <div class="pt-4 flex-1 min-w-0 flex items-center justify-center">Loading…</div>
  {:else if glStore.status === "not-yet-modelled"}
    <div class="pt-4 flex-1 min-w-0 flex">
      <NotYetModelled
        label="No GL data modelled for the selected company yet."
        class="flex-1 flex flex-col items-center justify-center"
      />
    </div>
  {:else}
    <div class="flex flex-col gap-4 pt-4 min-w-0">
      <div class="grid grid-cols-4 max-[900px]:grid-cols-2 gap-2.5">
        {#each financialKpis as kpi (kpi.id)}
          <KpiCard {kpi} />
        {/each}
      </div>

      <div class="flex max-[900px]:flex-col gap-4">
        <Card class="flex-1 min-w-0" title="Income Statement Key Items">
          <MonthlyTrendChart
            series={monthlyPerformanceChart}
            months={visibleMonthLabels}
            {currency}
            moneyScale={resolvedMoneyScale}
          />
        </Card>

        <Card class="flex-1 min-w-0" title="Profit Bridge: Revenue to NPAT">
          <ProfitBridge steps={profitBridgeSteps} height={300} {currency} moneyScale={resolvedMoneyScale} />
        </Card>
      </div>

      <Card>
        {#snippet header()}
          <div class="flex justify-between items-baseline mb-2">
            <div class="font-bold text-sm text-gray-900 dark:text-gray-50">
              Income Statement
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
                Show GL code
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
