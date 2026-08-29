<script lang="ts">
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
  import { months, formatRmAuto, cumulative } from "../lib/data/format";
  import type { DisplayRow, OperationalUnit } from "../lib/data/types";

  let ytdView = $state(false);

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

  let expandedGroups = $state<Set<string>>(new Set());
  let expandedGroupsInitialised = false;
  $effect(() => {
    if (expandedGroupsInitialised || pnlRows.length === 0) return;
    expandedGroupsInitialised = true;
    expandedGroups = new Set(
      [...collapsibleIds].filter((id) => !operationalGroupIds.has(id)),
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
      .map((row) => ({
        row,
        node: getNode(glStore.tree, row.nodeId),
        monthly: getNode(glStore.tree, row.nodeId)?.monthlyActual ?? [],
      }))
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

  const financialKpis = $derived(
    revenue && costOfRevenue && grossProfit && npat
      ? [
          {
            id: "revenue-ytd",
            label: "Revenue YTD",
            value: formatRmAuto(revenue.actual),
            trend: cumulative(revenue.monthlyActual),
          },
          {
            id: "cost-of-revenue-ytd",
            label: "Cost of Revenue YTD",
            value: formatRmAuto(Math.abs(costOfRevenue.actual)),
            trend: cumulative(costOfRevenue.monthlyActual.map(Math.abs)),
          },
          {
            id: "gross-profit-ytd",
            label: "Gross Profit YTD",
            value: formatRmAuto(grossProfit.actual),
            trend: cumulative(grossProfit.monthlyActual),
          },
          {
            id: "npat-ytd",
            label: "NPAT YTD",
            value: formatRmAuto(npat.actual),
            trend: cumulative(npat.monthlyActual),
          },
        ]
      : [],
  );

  const monthlyPerformanceChart = $derived(
    revenue && costOfRevenue && grossProfit && npat
      ? [
          { label: "Revenue", values: revenue.monthlyActual },
          { label: "COR", values: costOfRevenue.monthlyActual.map(Math.abs) },
          { label: "GP", values: grossProfit.monthlyActual },
          { label: "NPAT", values: npat.monthlyActual },
        ]
      : [],
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

  const statementGridCols =
    "grid-cols-[minmax(240px,1.3fr)_repeat(12,minmax(64px,1fr))]";

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
  <ContextBar showYtd bind:ytd={ytdView} />

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
          <MonthlyTrendChart series={monthlyPerformanceChart} {months} />
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
              class="grid {statementGridCols} items-center py-1 text-xs text-indigo-700 dark:text-indigo-300 border-b border-indigo-200 dark:border-indigo-900"
            >
              <span>Line item</span>
              {#each months as m (m)}
                <span class="flex items-center justify-end gap-1">
                  {m}
                  <svg class="w-3 h-3 shrink-0 invisible" viewBox="0 0 24 24"
                    ><circle cx="10.5" cy="10.5" r="6.5" /></svg
                  >
                </span>
              {/each}
            </div>
            {#snippet monthCell(nodeId: string, month: string, display: string)}
              <a
                class="group/cell flex items-center justify-end gap-1 no-underline text-inherit tabular-nums"
                href="/vdt/{nodeId}?month={month}"
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
                  class="grid {statementGridCols} items-center py-1.5 text-sm cursor-pointer text-gray-700 dark:text-gray-300 hover:bg-indigo-50 dark:hover:bg-indigo-950/40 {row.isSubtotal
                    ? 'font-bold bg-indigo-50 dark:bg-indigo-900/30 rounded'
                    : ''}"
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
                      months[i],
                      statementValue(value),
                    )}
                  {/each}
                </div>
              {:else if row.kind === "operational"}
                <div
                  transition:slide={{ duration: 150 }}
                  class="grid {statementGridCols} items-center py-1.5 text-sm text-amber-700 dark:text-amber-400 bg-amber-50/60 dark:bg-amber-400/10"
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
                  class="grid {statementGridCols} items-center py-1.5 text-sm text-gray-700 dark:text-gray-300 hover:bg-indigo-50 dark:hover:bg-indigo-950/40 {row.isSubtotal
                    ? 'font-bold bg-indigo-50 dark:bg-indigo-900/30 rounded'
                    : ''} {row.isFinal
                    ? 'bg-indigo-600 dark:bg-indigo-500 text-white rounded pl-1.5'
                    : ''}"
                >
                  <span
                    class={row.indent > 0
                      ? `${indentClass(row.indent)} text-gray-500 dark:text-gray-400`
                      : undefined}>{row.label}</span
                  >
                  {#each values as value, i (i)}
                    {@render monthCell(
                      row.nodeId,
                      months[i],
                      statementValue(value),
                    )}
                  {/each}
                </div>
              {/if}
            {/each}
          </div>
        </div>
        <div class="text-[10px] text-indigo-600 dark:text-indigo-400 mt-2">
          ▸ toggles a group open · hover a month value for the search icon →
          opens VDT Explorer scoped to that line + month ·
          <span class="text-amber-700 dark:text-amber-400"
            >amber "Ops" rows are operational value drivers, not GL amounts</span
          >
        </div>
      </Card>
    </div>
  {/if}
</PageBody>
