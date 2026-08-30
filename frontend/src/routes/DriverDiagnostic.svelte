<script lang="ts">
  import { link } from 'svelte-spa-router';
  import PageHeader from '../lib/components/PageHeader.svelte';
  import PageBody from '../lib/components/PageBody.svelte';
  import ContextBar from '../lib/components/ContextBar.svelte';
  import Sparkline from '../lib/components/Sparkline.svelte';
  import ChipRow from '../lib/components/ChipRow.svelte';
  import Badge from '../lib/components/Badge.svelte';
  import NotYetModelled from '../lib/components/NotYetModelled.svelte';
  import { glStore } from '../lib/data/gl-store.svelte';
  import { getNode, getAncestors } from '../lib/data/gl-client';
  import { periodState } from '../lib/state/period.svelte';
  import { formatRm, formatVar, pct } from '../lib/data/format';

  let { params }: { params: { id: string; tab?: string } } = $props();

  const node = $derived(getNode(glStore.tree, params.id));
  const tab = $derived(params.tab ?? 'diagnose');
  const ancestors = $derived(
    node ? getAncestors(glStore.tree, node.id).map((a) => ({ id: a.id, name: a.name, href: `/vdt/${a.id}?period=${periodState.code}` })) : []
  );

  // Locally-overridable statuses for Validate/Reject, keyed "nodeId:entryId".
  let statusOverrides = $state<Record<string, string>>({});
  function statusFor(entryId: string, fallback: string): string {
    return statusOverrides[`${params.id}:${entryId}`] ?? fallback;
  }
  function setStatus(entryId: string, status: string) {
    statusOverrides = { ...statusOverrides, [`${params.id}:${entryId}`]: status };
  }
</script>

{#if glStore.status === 'loading'}
  <PageHeader title="Driver Diagnostic" />
  <PageBody>Loading…</PageBody>
{:else if glStore.status === 'not-yet-modelled'}
  <PageHeader title="Driver Diagnostic" />
  <PageBody>
    <ContextBar />
    <NotYetModelled label="No GL data modelled for the selected company/BU yet." />
  </PageBody>
{:else if node}
  <PageHeader title={node.name} />
  <PageBody>
    <ContextBar {ancestors} />

    <div class="pt-4">
    <div class="flex gap-4 border-b-2 border-gray-900 dark:border-gray-50">
      <a
        class="pb-2 text-sm no-underline border-b-[3px] -mb-0.5 {tab === 'diagnose' ? 'text-gray-900 dark:text-gray-50 font-bold border-gray-900 dark:border-gray-50' : 'text-gray-500 dark:text-gray-400 border-transparent'}"
        href="/diagnostic/{node.id}/diagnose"
        use:link>Diagnose</a>
      <a
        class="pb-2 text-sm no-underline border-b-[3px] -mb-0.5 {tab === 'benchmark' ? 'text-gray-900 dark:text-gray-50 font-bold border-gray-900 dark:border-gray-50' : 'text-gray-500 dark:text-gray-400 border-transparent'}"
        href="/diagnostic/{node.id}/benchmark"
        use:link>Benchmark</a>
      <a
        class="pb-2 text-sm no-underline border-b-[3px] -mb-0.5 {tab === 'rootcause' ? 'text-gray-900 dark:text-gray-50 font-bold border-gray-900 dark:border-gray-50' : 'text-gray-500 dark:text-gray-400 border-transparent'}"
        href="/diagnostic/{node.id}/rootcause"
        use:link>Root Cause &amp; Mitigation</a>
    </div>

    <div class="pt-4 flex flex-col gap-4">
      {#if tab === 'diagnose'}
        <div class="flex gap-6 items-center">
          <div><span class="text-xs text-gray-500 dark:text-gray-400">Actual</span><div class="font-bold text-lg">{formatRm(Math.abs(node.actual))}</div></div>
          <div><span class="text-xs text-gray-500 dark:text-gray-400">Budget</span><div class="font-bold text-lg">{formatRm(Math.abs(node.budget))}</div></div>
          <div>
            <span class="text-xs text-gray-500 dark:text-gray-400">Var%</span>
            <div class="font-bold text-lg {node.direction === 'adverse' ? 'text-red-600 dark:text-red-400' : node.direction === 'favourable' ? 'text-green-600 dark:text-green-400' : ''}">
              {formatVar(pct(node.actual, node.budget))}
            </div>
          </div>
          {#if node.priorYear !== undefined}
            <div><span class="text-xs text-gray-500 dark:text-gray-400">Prior Year</span><div class="font-bold text-lg">{formatRm(Math.abs(node.priorYear))}</div></div>
          {/if}
          <div class="ml-auto">
            <ChipRow chips={['YTD', 'MTD', 'QTD']} selected="YTD" />
          </div>
        </div>

        {#if node.monthlyActual.length}
          <div class="border border-gray-200 dark:border-gray-700 p-2"><Sparkline points={node.monthlyActual} width={860} height={52} /></div>
        {/if}

        {#if node.hasFullData && node.drivers && node.sensitivity}
          <div class="flex gap-4">
            <div class="flex-1 border-[1.5px] border-gray-200 dark:border-gray-700 rounded-lg py-2.5 px-4 bg-white dark:bg-gray-800">
              <div class="font-bold text-sm mb-2">Variance contribution — ranked</div>
              <div class="grid grid-cols-[1.3fr_0.6fr_0.6fr_0.5fr] text-xs text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-700 py-1"><span>Driver</span><span>Abs.</span><span>%</span><span>Dir.</span></div>
              {#each node.drivers as d (d.id)}
                <div class="grid grid-cols-[1.3fr_0.6fr_0.6fr_0.5fr] text-sm py-1">
                  <span>{d.label}</span>
                  <span>{d.varAbs.toFixed(1)}m</span>
                  <span>{d.varPct}%</span>
                  <span class="text-red-600 dark:text-red-400">▲</span>
                </div>
              {/each}
            </div>
            <div class="flex-1 border-[1.5px] border-gray-200 dark:border-gray-700 rounded-lg py-2.5 px-4 bg-white dark:bg-gray-800">
              <div class="font-bold text-sm mb-2">Sensitivity / Variability</div>
              <div class="text-xs text-gray-500 dark:text-gray-400">Most sensitive to output</div>
              {#each node.sensitivity.mostSensitive as s, i (s)}
                <div class="text-sm">{i + 1}. {s}</div>
              {/each}
              <div class="text-xs text-gray-500 dark:text-gray-400 mt-2">Most variable period to period</div>
              {#each node.sensitivity.mostVariable as s, i (s)}
                <div class="text-sm">{i + 1}. {s}</div>
              {/each}
            </div>
          </div>

          <ChipRow label="Segment by:" chips={['Vessel', 'Vessel type', 'Voyage', 'Charter type', 'Customer', 'Cost centre']} selected="Vessel" />
        {:else}
          <NotYetModelled
            label="Contribution ranking and sensitivity analysis not yet modelled for {node.name}."
            linkHref="/diagnostic/PNL-0024"
            linkLabel="See the fully modelled example: Repairs & Maintenance"
          />
        {/if}
      {/if}

      {#if tab === 'benchmark'}
        {#if node.benchmark}
          <div class="font-bold text-sm mb-2">Metric: {node.benchmark.metricLabel}</div>
          <div class="inline-block border-[1.5px] border-dashed border-blue-600 dark:border-blue-400 text-blue-600 dark:text-blue-400 rounded-lg py-2 px-2.5 text-xs">Comparison basis: {node.benchmark.basis}</div>
          <div class="flex gap-5 items-end border-b border-gray-100 dark:border-gray-800 px-4 pt-4 h-[110px]">
            {#each node.benchmark.bars as bar (bar.id)}
              <div class="flex flex-col items-center gap-1 w-20">
                <div
                  class="w-[60px] {bar.kind === 'subject' ? 'bg-red-600 dark:bg-red-400' : bar.kind === 'external' ? 'bg-gray-500 dark:bg-gray-400' : 'bg-gray-900 dark:bg-gray-50'}"
                  style="height:{(bar.valuePerVod / 4120) * 90}px"
                ></div>
                <div class="text-[10px] text-gray-700 dark:text-gray-300 text-center">{bar.label}</div>
              </div>
            {/each}
          </div>
          <div class="flex-1 border-[1.5px] border-gray-200 dark:border-gray-700 rounded-lg py-2.5 px-4 bg-white dark:bg-gray-800">
            <div class="grid grid-cols-[1.2fr_0.6fr_0.6fr] text-xs text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-700 py-1"><span>Basis</span><span>Value/VOD</span><span>Gap</span></div>
            {#each node.benchmark.rows as r (r.basis)}
              <div class="grid grid-cols-[1.2fr_0.6fr_0.6fr] text-sm py-1">
                <span>{r.basis}</span><span>{r.valuePerVod}</span><span>{r.gap}</span>
              </div>
            {/each}
          </div>
        {:else}
          <NotYetModelled
            label="Benchmark comparison not yet modelled for {node.name}."
            linkHref="/diagnostic/PNL-0024/benchmark"
            linkLabel="See the fully modelled example: Repairs & Maintenance"
          />
        {/if}
      {/if}

      {#if tab === 'rootcause'}
        {#if node.rootCause}
          <div class="text-xs text-gray-500 dark:text-gray-400">{node.reviewSummary}</div>
          {#each node.rootCause as entry (entry.id)}
            <div class="rounded-lg py-2.5 px-4 {entry.type === 'AI_HYPOTHESIS' ? 'border-[1.5px] border-dashed border-blue-600 dark:border-blue-400 bg-blue-50 dark:bg-blue-950' : 'border-[1.5px] border-gray-900 dark:border-gray-50 bg-white dark:bg-gray-800'}">
              <div class="flex justify-between items-baseline gap-2.5">
                <b class={entry.type === 'AI_HYPOTHESIS' ? 'text-blue-600 dark:text-blue-400' : ''}>{entry.driverLabel} ({entry.amountLabel})</b>
                <Badge variant={entry.type === 'FACT' ? 'fact' : 'ai'} text={entry.type === 'FACT' ? 'FACT' : 'AI HYPOTHESIS'} />
              </div>
              <div class="text-sm text-gray-700 dark:text-gray-300 mt-1">{entry.evidenceOrRationale}</div>
              {#if entry.mitigation}<div class="text-sm text-gray-700 dark:text-gray-300 mt-1">{entry.mitigation}</div>{/if}
              <div class="text-xs text-gray-500 dark:text-gray-400 mt-2">
                Status: <span class="border border-gray-900 dark:border-gray-50 rounded-full px-2 text-gray-900 dark:text-gray-50">{statusFor(entry.id, entry.status)}</span>
                {#if entry.type === 'AI_HYPOTHESIS' && statusFor(entry.id, entry.status) === 'AI proposed'}
                  · <button
                    class="border border-gray-900 dark:border-gray-50 bg-white dark:bg-gray-800 rounded-full py-px px-2 text-[10px] cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-900"
                    onclick={() => setStatus(entry.id, 'Validated')}>Validate</button>
                  <button
                    class="border border-gray-900 dark:border-gray-50 bg-white dark:bg-gray-800 rounded-full py-px px-2 text-[10px] cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-900"
                    onclick={() => setStatus(entry.id, 'Rejected')}>Reject</button>
                {/if}
                {#if entry.analystNotes}
                  · Analyst notes: {entry.analystNotes}
                {:else if entry.type === 'AI_HYPOTHESIS'}
                  · Analyst notes: <i>click to add…</i>
                {/if}
              </div>
            </div>
          {/each}
        {:else}
          <NotYetModelled
            label="Root cause & mitigation not yet modelled for {node.name}."
            linkHref="/diagnostic/PNL-0024/rootcause"
            linkLabel="See the fully modelled example: Repairs & Maintenance"
          />
        {/if}
      {/if}
    </div>
    </div>
  </PageBody>
{:else}
  <PageHeader title="Unknown node" />
  <PageBody>Unknown node: {params.id}</PageBody>
{/if}
