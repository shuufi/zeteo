<script lang="ts">
  import { link } from "svelte-spa-router";
  import { context } from "../data/zeteo-data";
  import BusinessPicker from "./BusinessPicker.svelte";
  import PeriodPicker from "./PeriodPicker.svelte";
  import ChipSelect from "./ChipSelect.svelte";
  import NodePicker from "./NodePicker.svelte";
  import PeriodSelect from "./PeriodSelect.svelte";
  import { scopeState } from "../state/scope.svelte";
  import { scopeDraft } from "../state/scope-draft.svelte";
  import { periodState } from "../state/period.svelte";
  import { periodDraft } from "../state/period-draft.svelte";
  import { loadScope } from "../data/gl-store.svelte";
  import { vdtStore, loadVdtScope } from "../data/vdt-store.svelte";
  import { periodStore, periodYearOf } from "../data/period-store.svelte";
  import type { PeriodType } from "../data/types";
  import {
    moneyScaleControlLabel,
    moneyScaleOptions,
    resolveMoneyScale,
    type MoneyScaleChoice,
  } from "../data/format";

  const comparisonOptions = ["vs Budget", "vs Last Year", "vs This Year"];

  // Business/Period stage a draft when picked (see docs/adr/0027); VDT
  // Variance Analysis supplies its own staged comparison commit callback.
  function applyPending(): void {
    const hasContextDraft = scopeDraft.dirty || periodDraft.dirty;
    if (hasContextDraft) {
      scopeState.set(scopeDraft.code, scopeDraft.label);
      periodState.set(periodDraft.code);
      loadScope(scopeDraft.code, periodDraft.code);
      // Only refresh the VDT tree if this session has already settled a load
      // for it at least once (visited a /vdt* route) — its default 'loading'
      // status before that first visit means "never fetched," not "in
      // flight," so this avoids an unconditional second fetch on every Apply
      // for users who never touch VDT Explorer.
      if (vdtStore.status === "ready" || vdtStore.status === "not-yet-modelled" || vdtStore.status === "error") {
        loadVdtScope(scopeDraft.code, periodDraft.code);
      }
      scopeDraft.reset();
      periodDraft.reset();
      moneyScale = "auto";
    }
    onVdtComparisonApply();
  }

  interface Crumb {
    id: string;
    name: string;
    href: string;
  }

  let {
    ancestors = [],
    currentLabel = "",
    refreshedAt = "",
    showYtd = false,
    ytdLabel = "YTD",
    showPeriod = true,
    periodYearOnly = false,
    ytd = $bindable(false),
    showTrendsMode = false,
    trendsMode = $bindable<"financial-year" | "trailing">("financial-year"),
    trailingAnchor = $bindable<string | undefined>(undefined),
    showSource = false,
    source = $bindable<"actual" | "budget">("actual"),
    showComparison = false,
    comparisonNode = $bindable<string | undefined>(undefined),
    grain = $bindable<PeriodType>("Month"),
    periodA = $bindable<string | undefined>(undefined),
    periodB = $bindable<string | undefined>(undefined),
    vdtComparison = false,
    vdtComparisonMode = $bindable("vs This Year"),
    vdtComparisonPeriodType = $bindable<PeriodType>("Month"),
    vdtPeriodA = $bindable<string | undefined>(undefined),
    vdtPeriodB = $bindable<string | undefined>(undefined),
    vdtComparisonDirty = false,
    onVdtComparisonApply = () => {},
    showComparisonChip = true,
    showMoneyScale = false,
    currency = "",
    moneyValues = [],
    moneyScale = $bindable<MoneyScaleChoice>("auto"),
  }: {
    ancestors?: Crumb[];
    currentLabel?: string;
    refreshedAt?: string;
    showYtd?: boolean;
    /** Label for the cumulative-sum toggle — "YTD" everywhere except VDT
     * Trends' Trailing mode, where "Cumulative" is the mode-agnostic term
     * (see docs/adr/0042; the toggle mechanism itself is unchanged, only
     * what it's labelled). */
    ytdLabel?: string;
    showPeriod?: boolean;
    /** Restricts the Period picker to Year-level nodes only, no Quarter/Month
     * drill-down — for screens whose whole point is a full fiscal year at
     * once (see docs/adr/0039). */
    periodYearOnly?: boolean;
    ytd?: boolean;
    /** VDT Trends' Financial Year / Trailing mode selector (see
     * docs/adr/0042) — Financial Year reuses the existing Year-only Period
     * picker; Trailing replaces it with an anchor-Month picker. Both apply
     * live, no Apply-button staging (unlike Business/Period). */
    showTrendsMode?: boolean;
    trendsMode?: "financial-year" | "trailing";
    trailingAnchor?: string;
    /** The Actual/Budget data-selection chip (see docs/adr/0039) — distinct
     * from the vs Budget/Last Year/This Year comparison chip below. */
    showSource?: boolean;
    source?: "actual" | "budget";
    showComparison?: boolean;
    comparisonNode?: string;
    grain?: PeriodType;
    periodA?: string;
    periodB?: string;
    /** Activates vs Last Year/vs This Year live on this ContextBar instance —
     * everywhere else the chip stays decorative (ADR-0005). See docs/adr/0034. */
    vdtComparison?: boolean;
    vdtComparisonMode?: string;
    vdtComparisonPeriodType?: PeriodType;
    vdtPeriodA?: string;
    vdtPeriodB?: string;
    vdtComparisonDirty?: boolean;
    onVdtComparisonApply?: () => void;
    /** The vs Budget/vs Last Year/vs This Year chip that stays decorative
     * everywhere it isn't wired live (ADR-0005) — set false to omit it
     * entirely on screens it has no bearing on at all. */
    showComparisonChip?: boolean;
    showMoneyScale?: boolean;
    currency?: string;
    moneyValues?: number[];
    moneyScale?: MoneyScaleChoice;
  } = $props();

  const automaticMoneyScale = $derived(resolveMoneyScale("auto", moneyValues));
  const moneyScaleValues = moneyScaleOptions.map((o) => o.value);
  const moneyScaleLabels = $derived(
    moneyScaleOptions.map((o) => (o.value === "auto" ? moneyScaleControlLabel("auto", automaticMoneyScale) : o.label)),
  );

  // VDT Variance Analysis compares a same-type Month, Quarter, or Year within
  // the current fiscal year (ADR-0042). `vs Last Year` derives the matching
  // earlier Period, so it needs only one picker.
  const vdtCurrentYearId = $derived(periodYearOf(periodState.code));
  const vdtPeriods = $derived(
    Object.values(periodStore.tree)
      .filter(
        (p) =>
          p.periodType === vdtComparisonPeriodType &&
          (p.id === vdtCurrentYearId || p.id.startsWith(`${vdtCurrentYearId}-`)),
      )
      .sort((a, b) => a.order - b.order),
  );
  const vdtComparisonOptions = $derived(
    vdtComparisonPeriodType === "Year"
      ? ["vs Budget", "vs Last Year"]
      : comparisonOptions,
  );

  // Trailing mode's anchor picker (see docs/adr/0042) lists every Month
  // across every fiscal year sibling root, chronological order — unlike
  // vdtYearMonths above, it deliberately isn't restricted to one fiscal year.
  const allMonthsChronological = $derived(
    Object.values(periodStore.tree)
      .filter((p) => p.periodType === "Month")
      .sort((a, b) => {
        const yearOrderOf = (code: string) => periodStore.tree[periodYearOf(code) ?? ""]?.order ?? 0;
        return yearOrderOf(a.id) - yearOrderOf(b.id) || a.order - b.order;
      }),
  );

  const grains: PeriodType[] = ["Month", "Quarter", "Year"];

  const periodsForGrain = $derived({
    Month: Object.values(periodStore.tree)
      .filter((p) => p.periodType === "Month")
      .sort((a, b) => a.order - b.order),
    Quarter: Object.values(periodStore.tree)
      .filter((p) => p.periodType === "Quarter")
      .sort((a, b) => a.order - b.order),
    Year: Object.values(periodStore.tree)
      .filter((p) => p.periodType === "Year")
      .sort((a, b) => a.order - b.order),
  });

  // Comparing two periods only makes sense at the same grain (see docs/adr/0031)
  // — switching grain clears both picks rather than leaving a stale cross-grain pair.
  function setGrain(g: PeriodType): void {
    if (g === grain) return;
    grain = g;
    periodA = undefined;
    periodB = undefined;
  }

  function setVdtComparisonPeriodType(periodType: PeriodType): void {
    if (periodType === vdtComparisonPeriodType) return;
    vdtComparisonPeriodType = periodType;
    if (periodType === "Year" && vdtComparisonMode === "vs This Year")
      vdtComparisonMode = "vs Last Year";
  }
</script>

<div
  class="flex items-center gap-2.5 pb-4 text-xs flex-wrap border-b border-gray-200 dark:border-gray-700"
>
  <BusinessPicker />
  {#if showTrendsMode}
    <ChipSelect
      id="trends-mode-select"
      options={["financial-year", "trailing"]}
      labels={["Financial Year", "Trailing"]}
      bind:selected={trendsMode}
    />
  {/if}
  {#if showPeriod && (!showTrendsMode || trendsMode === "financial-year")}
    <PeriodPicker yearOnly={periodYearOnly} />
  {/if}
  {#if showTrendsMode && trendsMode === "trailing"}
    <PeriodSelect label="Ending" periods={allMonthsChronological} bind:value={trailingAnchor} />
  {/if}
  {#if showSource}
    <ChipSelect
      id="source-select"
      options={["actual", "budget"]}
      labels={["Actual", "Budget"]}
      bind:selected={source}
    />
  {/if}
  {#if showComparison}
    <div class="w-72">
      <NodePicker bind:value={comparisonNode} />
    </div>

    <div class="flex items-center gap-1.5">
      <span class="text-xs whitespace-nowrap text-gray-500 dark:text-gray-400">Grain:</span>
      <div class="inline-flex rounded-md shadow-xs">
        {#each grains as g (g)}
          <button
            type="button"
            onclick={() => setGrain(g)}
            disabled={periodsForGrain[g].length < 2}
            class="px-3 py-1.5 text-xs font-medium border first:rounded-l-md last:rounded-r-md -ml-px first:ml-0 disabled:cursor-not-allowed disabled:opacity-40 {grain === g
              ? 'bg-indigo-600 border-indigo-600 text-white z-10'
              : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50 dark:bg-white/5 dark:border-white/10 dark:text-gray-300 dark:hover:bg-white/10'}"
          >
            {g}
          </button>
        {/each}
      </div>
    </div>

    <PeriodSelect label="Period A" periods={periodsForGrain[grain]} bind:value={periodA} />
    <span class="text-gray-400 dark:text-gray-500">vs</span>
    <PeriodSelect label="Period B" periods={periodsForGrain[grain]} bind:value={periodB} />
  {/if}
  {#if vdtComparison}
    <ChipSelect id="comparison-select" options={vdtComparisonOptions} bind:selected={vdtComparisonMode} />
    <div class="flex items-center gap-1.5">
      <span class="text-xs whitespace-nowrap text-gray-500 dark:text-gray-400">Compare by:</span>
      <div class="inline-flex rounded-md shadow-xs">
        {#each grains as periodType (periodType)}
          <button
            type="button"
            onclick={() => setVdtComparisonPeriodType(periodType)}
            class="px-3 py-1.5 text-xs font-medium border first:rounded-l-md last:rounded-r-md -ml-px first:ml-0 {vdtComparisonPeriodType === periodType
              ? 'bg-indigo-600 border-indigo-600 text-white z-10'
              : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50 dark:bg-white/5 dark:border-white/10 dark:text-gray-300 dark:hover:bg-white/10'}"
          >
            {periodType}
          </button>
        {/each}
      </div>
    </div>
    {#if vdtComparisonMode === "vs This Year"}
      <PeriodSelect label="Period A" periods={vdtPeriods} bind:value={vdtPeriodA} />
      <span class="text-gray-400 dark:text-gray-500">vs</span>
      <PeriodSelect label="Period B" periods={vdtPeriods} bind:value={vdtPeriodB} />
    {:else if vdtComparisonMode === "vs Last Year"}
      <PeriodSelect label="Period" periods={vdtPeriods} bind:value={vdtPeriodA} />
    {/if}
  {:else if showComparisonChip}
    <ChipSelect
      id="comparison-select"
      options={comparisonOptions}
      selected={context.comparison}
    />
  {/if}
  {#if showMoneyScale && currency}
    <ChipSelect
      id="money-scale-select"
      prefix="Scale:"
      options={moneyScaleValues}
      labels={moneyScaleLabels}
      bind:selected={moneyScale}
    />
  {/if}
  {#if showYtd}
    <label
      class="flex items-center gap-1.5 text-xs text-gray-600 dark:text-gray-300 cursor-pointer select-none"
    >
      <input
        type="checkbox"
        bind:checked={ytd}
        class="accent-indigo-600 dark:accent-indigo-400"
      />
      {ytdLabel}
    </label>
  {/if}
  <button
    type="button"
    onclick={applyPending}
    disabled={!scopeDraft.dirty && !periodDraft.dirty && !vdtComparisonDirty}
    class="rounded-md bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white shadow-xs hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-gray-300 disabled:text-gray-500 dark:disabled:bg-gray-700 dark:disabled:text-gray-400"
  >
    Apply
  </button>

  {#if ancestors.length || currentLabel}
    <span class="ml-2 text-gray-700 dark:text-gray-300 text-sm">
      {#each ancestors as crumb, i (crumb.id)}
        <a
          href={crumb.href}
          use:link
          class="text-gray-500 dark:text-gray-400 no-underline hover:text-indigo-600 dark:hover:text-indigo-400 hover:underline"
          >{crumb.name}</a
        >
        {#if i < ancestors.length - 1 || currentLabel}<span
            class="text-gray-500 dark:text-gray-400 mx-1">›</span
          >{/if}
      {/each}
      {#if currentLabel}<strong>{currentLabel}</strong>{/if}
    </span>
  {/if}

  {#if refreshedAt}
    <span class="ml-auto text-gray-500 dark:text-gray-400 whitespace-nowrap"
      >{refreshedAt}</span
    >
  {/if}
</div>
