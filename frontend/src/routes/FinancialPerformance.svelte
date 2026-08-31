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

  // Financial Performance always shows the whole fiscal year — unlike VDT
  // Explorer/Driver Diagnostic, it doesn't scope to the Period chip (see
  // docs/adr/0026, reverted from genuinely scoping per follow-up feedback):
  // its Income Statement is a grid of all 12 month columns and its KPI cards
  // are explicitly YTD, so the chip stays visible/interactive here (picking
  // still affects the other two screens) but this page ignores it.
  const visibleMonthIndices = $derived(monthPeriodCodes.map((_, i) => i));
  const gridTemplateColumns = $derived(
    `minmax(240px,1.3fr) repeat(${visibleMonthIndices.length}, minmax(64px,1fr))`,
  );
  const periodQualifier = "YTD";

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

  const financialKpis = $derived(
    revenue && costOfRevenue && grossProfit && npat
      ? [
          {
            id: "revenue-ytd",
            label: `Revenue ${periodQualifier}`,
            value: formatRmAuto(revenue.actual),
            trend: cumulative(scoped(revenue.monthlyActual)),
          },
          {
            id: "cost-of-revenue-ytd",
            label: `Cost of Revenue ${periodQualifier}`,
            value: formatRmAuto(Math.abs(costOfRevenue.actual)),
            trend: cumulative(
              scoped(costOfRevenue.monthlyActual).map(Math.abs),
            ),
          },
          {
            id: "gross-profit-ytd",
            label: `Gross Profit ${periodQualifier}`,
            value: formatRmAuto(grossProfit.actual),
            trend: cumulative(scoped(grossProfit.monthlyActual)),
          },
          {
            id: "npat-ytd",
            label: `NPAT ${periodQualifier}`,
            value: formatRmAuto(npat.actual),
            trend: cumulative(scoped(npat.monthlyActual)),
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
    unit: OperationalUnit | undefined,
  ): string {
    switch (unit) {
      case "usd-per-day":
        return `$${value.toFixed(0)}k/d`;
      case "usd-per-month":
        return `$${value.toFixed(0)}k/mo`;
      case "percent":
        return `${value.toFixed(1)}%`;
      case "days":
        return value.toFixed(1);
      case "count":
        return value.toFixed(0);
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
            <div class="text-xs text-gray-500 dark:text-gray-400">
              RM millions
            </div>
          </div>
        {/snippet}
        <div class="overflow-x-auto">
          <div class="flex flex-col min-w-[1080px]">
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
            {#each displayRows as { row, values } (row.nodeId)}
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
                  class="grid items-center py-1.5 text-sm cursor-pointer text-gray-700 dark:text-gray-300 hover:bg-indigo-50 dark:hover:bg-indigo-950/40 {row.isSubtotal
                    ? 'font-bold bg-indigo-50 dark:bg-indigo-900/30 rounded'
                    : ''}"
                  style="grid-template-columns: {gridTemplateColumns}"
                >
                  <span
                    class="flex items-center gap-1.5 {indentClass(
                      row.indent,
                    )} {row.indent > 0
                      ? 'text-gray-500 dark:text-gray-400'
                      : ''}"
                  >
                    <span
                      class="inline-block w-4 text-base leading-none text-indigo-600 dark:text-indigo-400 transition-transform duration-150 {expandedGroups.has(
                        row.nodeId,
                      )
                        ? 'rotate-90'
                        : ''}"
                    >
                      ▸
                    </span>
                    {row.label}
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
              {:else if row.kind === "operational"}
                <div
                  transition:slide={{ duration: 150 }}
                  class="grid items-center py-1.5 text-sm text-amber-700 dark:text-amber-400 bg-amber-50/60 dark:bg-amber-400/10"
                  style="grid-template-columns: {gridTemplateColumns}"
                >
                  <span
                    class="{indentClass(row.indent)} flex items-center gap-1.5"
                  >
                    <span
                      class="text-[9px] uppercase tracking-wide font-semibold text-amber-600 dark:text-amber-400 border border-amber-300 dark:border-amber-400/40 rounded px-1"
                      >Ops</span
                    >
                    {row.label}
                  </span>
                  {#each values as value, i (i)}
                    <span class="text-right tabular-nums"
                      >{operationalValue(value, row.unit)}</span
                    >
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
                    class={row.indent > 0
                      ? `${indentClass(row.indent)} text-gray-500 dark:text-gray-400`
                      : undefined}>{row.label}</span
                  >
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
