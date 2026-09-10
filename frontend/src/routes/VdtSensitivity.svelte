<script lang="ts">
  import { onMount } from "svelte";
  import PageHeader from "../lib/components/PageHeader.svelte";
  import PageBody from "../lib/components/PageBody.svelte";
  import ContextBar from "../lib/components/ContextBar.svelte";
  import Card from "../lib/components/Card.svelte";
  import NotYetModelled from "../lib/components/NotYetModelled.svelte";
  import LottieLoader from "../lib/components/LottieLoader.svelte";
  import VdtScopePicker from "../lib/components/VdtScopePicker.svelte";
  import TornadoChart from "../lib/components/TornadoChart.svelte";
  import SensitivityTable from "../lib/components/SensitivityTable.svelte";
  import SensitivityProgress from "../lib/components/SensitivityProgress.svelte";
  import { vdtStore, loadVdtScope } from "../lib/data/vdt-store.svelte";
  import {
    sensitivityStore,
    startSensitivity,
  } from "../lib/data/sensitivity-analysis-store.svelte";
  import {
    periodStore,
    loadPeriods,
    periodYearOf,
    trailingWindowMonths,
  } from "../lib/data/period-store.svelte";
  import { periodState } from "../lib/state/period.svelte";
  import { scopeState } from "../lib/state/scope.svelte";
  import { resolveMoneyScale, type MoneyScaleChoice } from "../lib/data/format";

  let scopeNode = $state<string | undefined>(undefined);
  let bumpPct = $state(10);
  let moneyScale = $state<MoneyScaleChoice>("auto");
  let source = $state<"actual" | "budget">("actual");

  // Financial Year (default) vs Trailing — same picker VDT Trends uses (see
  // docs/adr/0042/0043).
  let trendsMode = $state<"financial-year" | "trailing">("financial-year");
  let trailingAnchor = $state<string | undefined>(undefined);

  onMount(loadPeriods);

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

  // vdtStore isn't populated app-wide — this screen owns its own fetch, the
  // same pattern VdtTrends uses, since VdtScopePicker needs a populated
  // vdtStore.tree to offer scope candidates.
  let lastFetchKey = "";
  $effect(() => {
    const anchor = trendsMode === "trailing" ? trailingAnchor : currentYearId;
    if (!anchor) return;
    const key = `${scopeState.code}:${trendsMode}:${anchor}`;
    if (key === lastFetchKey) return;
    const isFirstRun = lastFetchKey === "";
    lastFetchKey = key;
    if (isFirstRun && vdtStore.status === "ready") return;
    if (trendsMode === "trailing") {
      loadVdtScope(scopeState.code, undefined, anchor);
    } else {
      loadVdtScope(scopeState.code, anchor);
    }
  });

  // Default scope = the whole book (VDT tree's Reporting Root) — set once
  // the tree loads, only if the user hasn't already picked a scope.
  $effect(() => {
    if (scopeNode) return;
    const root = Object.values(vdtStore.tree).find((n) => n.parentId === null);
    if (root) scopeNode = root.id;
  });

  const window = $derived(
    trendsMode === "trailing"
      ? trailingAnchor
        ? ({ trailingEnd: trailingAnchor } as const)
        : undefined
      : currentYearId
        ? ({ year: currentYearId } as const)
        : undefined,
  );

  function handleRun(): void {
    if (!scopeNode || !window) return;
    startSensitivity({ scope: scopeState.code, scopeNode, bumpPct, source, window });
  }

  // Reset a stale result when the underlying window/scope/bump/source
  // changes, so a stale chart never lingers after the inputs move — mirrors
  // Trends/Variance Analysis's reset-on-key-change pattern.
  let lastRunKey = "";
  $effect(() => {
    const anchor = trendsMode === "trailing" ? trailingAnchor : currentYearId;
    const key = `${scopeState.code}:${trendsMode}:${anchor}:${source}:${scopeNode ?? ""}:${bumpPct}`;
    if (lastRunKey && key !== lastRunKey) sensitivityStore.reset();
    lastRunKey = key;
  });

  const currency = $derived(sensitivityStore.result?.currency ?? vdtStore.meta?.currency ?? "");
  const moneyValues = $derived(
    (sensitivityStore.result?.candidates ?? []).flatMap((c) => [c.up.npatImpact, c.down.npatImpact]),
  );
  const resolvedMoneyScale = $derived(resolveMoneyScale(moneyScale, moneyValues));

  // Provisional top-10 among whatever's streamed in so far, re-derived as
  // each `candidate` event lands — rank order isn't stable until the run
  // finishes (see the store's liveCandidates doc comment), so this is a
  // preview, not the authoritative list `result.ranked` replaces it with.
  const liveRanked = $derived(
    [...sensitivityStore.liveCandidates]
      .filter((c) => !c.na)
      .sort((a, b) => (b.rankMagnitude ?? -1) - (a.rankMagnitude ?? -1))
      .slice(0, 10),
  );
  const liveMoneyValues = $derived(
    sensitivityStore.liveCandidates.flatMap((c) => [c.up.npatImpact, c.down.npatImpact]),
  );
  const liveMoneyScale = $derived(resolveMoneyScale(moneyScale, liveMoneyValues));
</script>

<PageHeader title="VDT Sensitivity Analysis" />
<PageBody>
  <ContextBar
    showTrendsMode
    bind:trendsMode
    bind:trailingAnchor
    showPeriod
    periodYearOnly
    showSource
    bind:source
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
    <div class="flex flex-col gap-4 pt-4 min-w-0">
      <Card title="Run Sensitivity">
        <div class="flex flex-wrap items-end gap-4">
          <VdtScopePicker bind:value={scopeNode} />
          <label class="flex flex-col gap-1 text-xs text-gray-500 dark:text-gray-400">
            Bump %
            <input
              type="number"
              min="1"
              max="20"
              step="1"
              bind:value={bumpPct}
              class="w-20 rounded-md bg-white py-1.5 px-2 text-sm text-gray-900 outline-1 -outline-offset-1 outline-gray-300 focus:outline-2 focus:-outline-offset-2 focus:outline-indigo-600 dark:bg-white/5 dark:text-white dark:outline-white/10"
            />
          </label>
          <button
            type="button"
            onclick={handleRun}
            disabled={sensitivityStore.status === "streaming" || !scopeNode || !window}
            class="rounded-md bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white shadow-xs hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-gray-300 disabled:text-gray-500 dark:disabled:bg-gray-700 dark:disabled:text-gray-400"
          >
            {sensitivityStore.status === "streaming" ? "Running…" : "Run Sensitivity"}
          </button>
        </div>
      </Card>

      {#if sensitivityStore.status === "streaming"}
        <Card>
          <SensitivityProgress progress={sensitivityStore.progress} />
        </Card>
        {#if liveRanked.length}
          <div class="flex flex-col gap-4 min-w-0 lg:flex-row">
            <div class="flex-1 min-w-0">
              <Card title="Top 10 Drivers by Elasticity to NPAT (running…)">
                <TornadoChart candidates={liveRanked} {currency} moneyScale={liveMoneyScale} />
              </Card>
            </div>
            <div class="flex-1 min-w-0">
              <Card title="Elasticity Detail (running…)">
                <SensitivityTable candidates={liveRanked} {currency} moneyScale={liveMoneyScale} {bumpPct} />
              </Card>
            </div>
          </div>
        {/if}
      {:else if sensitivityStore.status === "error"}
        <Card>
          <div class="text-xs text-red-600 dark:text-red-400">
            Unable to run sensitivity analysis right now ({sensitivityStore.error}).
          </div>
        </Card>
      {:else if sensitivityStore.status === "ready" && sensitivityStore.result}
        {@const result = sensitivityStore.result}
        {#if result.reason === "no-terminal-drivers"}
          <Card>
            <div class="text-sm text-gray-500 dark:text-gray-400">
              No terminal Drivers under the selected scope to test. Try widening the scope.
            </div>
          </Card>
        {:else if result.reason === "all-na" || result.ranked.length === 0}
          <Card>
            <div class="text-sm text-gray-500 dark:text-gray-400">
              {#if result.npatNearZero}
                Sensitivity is undefined for this window — NPAT is near zero, so elasticity can't be computed.
              {:else}
                Every candidate Driver resolved to N/A for this window.
              {/if}
            </div>
          </Card>
        {:else}
          <div class="flex flex-col gap-4 min-w-0 lg:flex-row">
            <div class="flex-1 min-w-0">
              <Card title="Top 10 Drivers by Elasticity to NPAT">
                <TornadoChart candidates={result.ranked} {currency} moneyScale={resolvedMoneyScale} />
              </Card>
            </div>
            <div class="flex-1 min-w-0">
              <Card title="Elasticity Detail">
                <SensitivityTable
                  candidates={result.ranked}
                  {currency}
                  moneyScale={resolvedMoneyScale}
                  bumpPct={result.bumpPct}
                />
              </Card>
            </div>
          </div>
        {/if}
      {/if}
    </div>
  {/if}
</PageBody>
