<script lang="ts">
  import { onMount } from "svelte";
  import { link } from "svelte-spa-router";
  import { slide } from "svelte/transition";
  import PageHeader from "../lib/components/PageHeader.svelte";
  import PageBody from "../lib/components/PageBody.svelte";
  import ContextBar from "../lib/components/ContextBar.svelte";
  import Card from "../lib/components/Card.svelte";
  import KpiCard from "../lib/components/KpiCard.svelte";
  import MonthlyTrendChart from "../lib/components/MonthlyTrendChart.svelte";
  import ProfitBridge from "../lib/components/ProfitBridge.svelte";
  import NotYetModelled from "../lib/components/NotYetModelled.svelte";
  import { glStore } from "../lib/data/gl-store.svelte";
  import {
    getNode,
    buildDisplayRows,
    indentClass,
  } from "../lib/data/gl-client";
  import { periodStore, loadPeriods } from "../lib/data/period-store.svelte";
  import { months, formatRmAuto, cumulative } from "../lib/data/format";
  import type { DisplayRow, OperationalUnit } from "../lib/data/types";

  let ytdView = $state(false);

  onMount(loadPeriods);

  // Month order (1-12) is global on Period.order (see docs/adr/0025), so a
  // plain numeric sort aligns 1:1 with `months` regardless of quarter.
  const monthPeriodCodes = $derived(
    Object.values(periodStore.tree)
      .filter((p) => p.periodType === "Month")
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

  // User-resizable via the drag handle next to the header — width persists
  // for the session but isn't saved beyond it (no ask for that).
  let lineItemWidth = $state(280);
  const LINE_ITEM_MIN_WIDTH = 160;
  const LINE_ITEM_MAX_WIDTH = 640;

  function startResize(event: PointerEvent): void {
    event.preventDefault();
    const startX = event.clientX;
    const startWidth = lineItemWidth;
    function onMove(e: PointerEvent): void {
      lineItemWidth = Math.min(
        LINE_ITEM_MAX_WIDTH,
        Math.max(LINE_ITEM_MIN_WIDTH, startWidth + (e.clientX - startX)),
      );
    }
    function onUp(): void {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
    }
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
  }

  // Off by default — the GL code is noise until you need to cross-reference
  // SAP, so it's opt-in via the checkbox next to the table title.
  let showGlCode = $state(false);
  function displayLabel(row: DisplayRow): string {
    return showGlCode ? `${row.nodeId} ${row.label}` : row.label;
  }

  const gridTemplateColumns = $derived(
    `${lineItemWidth}px repeat(${visibleMonthIndices.length}, minmax(64px,1fr))`,
  );

  const pnlRows = $derived(buildDisplayRows(glStore.tree));
  const rowsByNodeId = $derived(
    new Map(pnlRows.map((row) => [row.nodeId, row])),
  );
  const collapsibleIds = $derived(
    new Set(
      pnlRows
        .map((row) => row.group)
        .filter((g): g is string => g !== undefined),
    ),
  );
  // Groups whose children are purely operational drivers start collapsed — they're
  // supplementary detail, so the GL statement stays readable by default.
  const operationalGroupIds = $derived(
    new Set(
      pnlRows
        .filter((row) => row.kind === "operational")
        .map((row) => row.group)
        .filter((g): g is string => g !== undefined),
    ),
  );
  // Groups above hierarchy level 1 auto-expand; level 1 and deeper (Posting
  // GL Account leaves and whatever's nested under them) start collapsed — see
  // docs/adr/0029. A group's own row.indent tracks its real GL hierarchy
  // depth (walk() increments indent 1:1 with GLNode.level).
  const summaryGroupIds = $derived(
    new Set(
      [...collapsibleIds].filter(
        (id) => (rowsByNodeId.get(id)?.indent ?? 0) < 1,
      ),
    ),
  );

  let expandedGroups = $state<Set<string>>(new Set());
  let expandedGroupsInitialised = false;
  $effect(() => {
    if (expandedGroupsInitialised || pnlRows.length === 0) return;
    expandedGroupsInitialised = true;
    expandedGroups = new Set(
      [...summaryGroupIds].filter((id) => !operationalGroupIds.has(id)),
    );
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

  const rows = $derived(
    pnlRows
      .filter(isVisible)
      .map((row) => {
        const monthlyActual =
          getNode(glStore.tree, row.nodeId)?.monthlyActual ?? [];
        return {
          row,
          node: getNode(glStore.tree, row.nodeId),
          monthly: visibleMonthIndices.map((i) => monthlyActual[i] ?? 0),
        };
      })
      .filter((r) => r.row.kind === "operational" || r.node !== undefined),
  );

  const displayRows = $derived(
    rows.map((r) => ({
      ...r,
      // Cumulative sum is meaningless for rates/percentages/day-counts — operational
      // driver rows always show their monthly (period) value, regardless of the toggle.
      values:
        ytdView && r.row.kind !== "operational"
          ? cumulative(r.monthly)
          : r.monthly,
    })),
  );

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
      return `${month} (${year}): ${formatRmAuto(v)}`;
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
            value: formatRmAuto(revenue.actual),
            trend: revenueTrend.trend,
            trendTooltips: revenueTrend.tooltips,
            trendFillClass: "fill-gray-900 dark:fill-gray-50",
          },
          {
            id: "cost-of-revenue-ytd",
            label: "Cost of Revenue",
            value: formatRmAuto(Math.abs(costOfRevenue.actual)),
            trend: costOfRevenueTrend.trend,
            trendTooltips: costOfRevenueTrend.tooltips,
            trendFillClass: "fill-red-600 dark:fill-red-400",
          },
          {
            id: "gross-profit-ytd",
            label: "Gross Profit",
            value: formatRmAuto(grossProfit.actual),
            trend: grossProfitTrend.trend,
            trendTooltips: grossProfitTrend.tooltips,
            trendFillClass: "fill-emerald-600 dark:fill-emerald-400",
          },
          {
            id: "npat-ytd",
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

  // Values already carry the right sign server-side (see docs/adr/0023) — a
  // negative number is a subtraction/loss, shown in parens.
  function statementValue(value: number): string {
    const text = Math.abs(value).toFixed(1);
    return value < 0 && value !== 0 ? `(${text})` : text;
  }

  function operationalValue(
    value: number,
    unit: OperationalUnit | "RM_M" | undefined,
  ): string {
    switch (unit) {
      case "RM_M":
        // A Driver Formula bound to a GL leaf produces money — same signed,
        // parens-for-negative treatment as any other statement row.
        return statementValue(value);
      case "usd-per-day":
        // Small values (e.g. an RM_M-scaled Driver Formula term — see
        // docs/adr/0030) need more than 0 decimals or they'd all show "$0k/d".
        return value < 10 ? `$${value.toFixed(3)}k/d` : `$${value.toFixed(0)}k/d`;
      case "usd-per-month":
        return value < 10 ? `$${value.toFixed(3)}k/mo` : `$${value.toFixed(0)}k/mo`;
      case "percent":
        return `${value.toFixed(1)}%`;
      case "days":
        return value.toFixed(1);
      case "count":
        return value.toFixed(0);
      case "ratio":
        return `${value.toFixed(2)}×`;
      default:
        return value.toFixed(1);
    }
  }
</script>

<PageHeader title="Financial Trends" />
<PageBody>
  <ContextBar showYtd showPeriod={false} bind:ytd={ytdView} />

  {#if glStore.status === "loading"}
    <div class="pt-4">Loading…</div>
  {:else if glStore.status === "not-yet-modelled"}
    <div class="pt-4">
      <NotYetModelled
        label="No GL data modelled for the selected company/BU yet."
      />
    </div>
  {:else}
    <div class="flex flex-col gap-4 pt-4">
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
          />
        </Card>

        <Card class="flex-1 min-w-0" title="Profit Bridge: Revenue to NPAT">
          <ProfitBridge steps={profitBridgeSteps} height={300} />
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
                RM millions
              </div>
            </div>
          </div>
        {/snippet}
        <div class="overflow-x-auto">
          <div class="relative flex flex-col min-w-[1080px]">
            <div
              role="separator"
              aria-orientation="vertical"
              onpointerdown={startResize}
              class="absolute top-0 bottom-0 w-2.5 -translate-x-1/2 cursor-col-resize touch-none z-10 group/resize"
              style="left: {lineItemWidth}px"
            >
              <div
                class="mx-auto h-full w-px bg-transparent group-hover/resize:bg-indigo-400 dark:group-hover/resize:bg-indigo-500"
              ></div>
            </div>
            <div
              class="grid items-center py-1 text-xs text-indigo-700 dark:text-indigo-300 border-b border-indigo-200 dark:border-indigo-900"
              style="grid-template-columns: {gridTemplateColumns}"
            >
              <span>Line item</span>
              {#each visibleMonthIndices as monthIdx (monthIdx)}
                <span class="flex items-center justify-end gap-1">
                  {months[monthIdx]}
                  <svg class="w-3 h-3 shrink-0 invisible" viewBox="0 0 24 24"
                    ><circle cx="10.5" cy="10.5" r="6.5" /></svg
                  >
                </span>
              {/each}
            </div>
            {#snippet monthCell(
              nodeId: string,
              periodCode: string | undefined,
              month: string,
              display: string,
            )}
              {#if periodCode}
                <a
                  class="group/cell flex items-center justify-end gap-1 no-underline text-inherit tabular-nums"
                  href="/vdt/{nodeId}?period={periodCode}"
                  use:link
                  onclick={(e) => e.stopPropagation()}
                  title="Explore {month} in VDT Explorer"
                >
                  <span>{display}</span>
                  <svg
                    class="w-3 h-3 shrink-0 text-indigo-500 dark:text-indigo-400 opacity-0 group-hover/cell:opacity-100 transition-opacity"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2.5"
                  >
                    <circle cx="10.5" cy="10.5" r="6.5" />
                    <line x1="16" y1="16" x2="21" y2="21" />
                  </svg>
                </a>
              {:else}
                <!-- periods haven't loaded (or failed to) — plain text, no dead/undefined link -->
                <span class="flex items-center justify-end tabular-nums"
                  >{display}</span
                >
              {/if}
            {/snippet}
            {#snippet truncatedLabel(row: DisplayRow)}
              <span class="group/label relative min-w-0">
                <span class="truncate block">{displayLabel(row)}</span>
                <span
                  class="pointer-events-none absolute left-0 top-full z-30 mt-1 hidden whitespace-nowrap rounded bg-gray-900 dark:bg-gray-700 px-2 py-1 text-xs font-normal text-white shadow-lg group-hover/label:block"
                >
                  {displayLabel(row)}
                </span>
              </span>
            {/snippet}
            {#snippet operationalCells(row: DisplayRow, values: number[], isCollapsible: boolean)}
              <span class="{indentClass(row.indent)} flex flex-col min-w-0">
                <span class="flex items-center gap-1.5 min-w-0">
                  {#if isCollapsible}
                    <span
                      class="inline-block w-4 shrink-0 text-base leading-none text-amber-600 dark:text-amber-400 transition-transform duration-150 {expandedGroups.has(
                        row.nodeId,
                      )
                        ? 'rotate-90'
                        : ''}"
                    >
                      ▸
                    </span>
                  {/if}
                  <span
                    class="text-[9px] uppercase tracking-wide font-semibold text-amber-600 dark:text-amber-400 border border-amber-300 dark:border-amber-400/40 rounded px-1 shrink-0"
                    >{row.driverNodeType === "formula" ? "Formula" : "Ops"}</span
                  >
                  {@render truncatedLabel(row)}
                </span>
                {#if row.driverNodeType === "formula" && row.expression}
                  <span
                    class="truncate text-[10px] font-normal normal-case tracking-normal text-amber-600/70 dark:text-amber-400/60 {isCollapsible
                      ? 'pl-6'
                      : ''}"
                    title={row.expression}
                  >
                    {row.expression}
                  </span>
                {/if}
              </span>
              {#each values as value, i (i)}
                <span class="text-right tabular-nums"
                  >{operationalValue(value, row.unit)}</span
                >
              {/each}
            {/snippet}
            {#each displayRows as { row, values } (row.nodeId)}
              {#if row.kind === "operational"}
                {#if collapsibleIds.has(row.nodeId)}
                  <div
                    role="button"
                    tabindex="0"
                    onclick={() => toggleGroup(row.nodeId)}
                    onkeydown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        toggleGroup(row.nodeId);
                      }
                    }}
                    transition:slide={{ duration: 150 }}
                    class="grid items-center py-1.5 text-sm cursor-pointer text-amber-700 dark:text-amber-400 bg-amber-50/60 dark:bg-amber-400/10"
                    style="grid-template-columns: {gridTemplateColumns}"
                  >
                    {@render operationalCells(row, values, true)}
                  </div>
                {:else}
                  <div
                    transition:slide={{ duration: 150 }}
                    class="grid items-center py-1.5 text-sm text-amber-700 dark:text-amber-400 bg-amber-50/60 dark:bg-amber-400/10"
                    style="grid-template-columns: {gridTemplateColumns}"
                  >
                    {@render operationalCells(row, values, false)}
                  </div>
                {/if}
              {:else if collapsibleIds.has(row.nodeId)}
                <div
                  role="button"
                  tabindex="0"
                  onclick={() => toggleGroup(row.nodeId)}
                  onkeydown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      toggleGroup(row.nodeId);
                    }
                  }}
                  transition:slide={{ duration: 150 }}
                  class="grid items-center py-1.5 text-sm cursor-pointer text-gray-700 dark:text-gray-300 hover:bg-indigo-50 dark:hover:bg-indigo-950/40 {row.isSubtotal
                    ? 'font-bold bg-indigo-50 dark:bg-indigo-900/30 rounded'
                    : ''}"
                  style="grid-template-columns: {gridTemplateColumns}"
                >
                  <span
                    class="flex items-center gap-1.5 min-w-0 {indentClass(
                      row.indent,
                    )} {row.indent > 0
                      ? 'text-gray-500 dark:text-gray-400'
                      : ''}"
                  >
                    <span
                      class="inline-block w-4 shrink-0 text-base leading-none text-indigo-600 dark:text-indigo-400 transition-transform duration-150 {expandedGroups.has(
                        row.nodeId,
                      )
                        ? 'rotate-90'
                        : ''}"
                    >
                      ▸
                    </span>
                    {@render truncatedLabel(row)}
                  </span>
                  {#each values as value, i (i)}
                    {@render monthCell(
                      row.nodeId,
                      monthPeriodCodes[visibleMonthIndices[i]],
                      months[visibleMonthIndices[i]],
                      statementValue(value),
                    )}
                  {/each}
                </div>
              {:else}
                <div
                  transition:slide={{ duration: 150 }}
                  class="grid items-center py-1.5 text-sm text-gray-700 dark:text-gray-300 hover:bg-indigo-50 dark:hover:bg-indigo-950/40 {row.isSubtotal
                    ? 'font-bold bg-indigo-50 dark:bg-indigo-900/30 rounded'
                    : ''} {row.isFinal
                    ? 'bg-indigo-600 dark:bg-indigo-500 text-white rounded pl-1.5'
                    : ''}"
                  style="grid-template-columns: {gridTemplateColumns}"
                >
                  <span
                    class="flex min-w-0 {row.indent > 0
                      ? `${indentClass(row.indent)} text-gray-500 dark:text-gray-400`
                      : ''}"
                  >
                    {@render truncatedLabel(row)}
                  </span>
                  {#each values as value, i (i)}
                    {@render monthCell(
                      row.nodeId,
                      monthPeriodCodes[visibleMonthIndices[i]],
                      months[visibleMonthIndices[i]],
                      statementValue(value),
                    )}
                  {/each}
                </div>
              {/if}
            {/each}
          </div>
        </div>
      </Card>
    </div>
  {/if}
</PageBody>
