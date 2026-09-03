<script lang="ts">
  import { onMount } from 'svelte';
  import { link, router } from 'svelte-spa-router';
  import PageHeader from '../lib/components/PageHeader.svelte';
  import PageBody from '../lib/components/PageBody.svelte';
  import ContextBar from '../lib/components/ContextBar.svelte';
  import ValueDriverFlow from '../lib/components/ValueDriverFlow.svelte';
  import ChipRow from '../lib/components/ChipRow.svelte';
  import NotYetModelled from '../lib/components/NotYetModelled.svelte';
  import { vdtStore, loadVdtScope } from '../lib/data/vdt-store.svelte';
  import { getNode, getAncestors, rankChildren } from '../lib/data/gl-client';
  import { periodState, DEFAULT_PERIOD_CODE } from '../lib/state/period.svelte';
  import { periodStore, periodLabel } from '../lib/data/period-store.svelte';
  import { scopeState } from '../lib/state/scope.svelte';
  import { formatVar, pct } from '../lib/data/format';

  let { params }: { params: { id: string } } = $props();

  const periodCode = $derived(new URLSearchParams(router.querystring ?? '').get('period'));
  const periodQuery = $derived(`?period=${periodState.code}`);
  // Explicit truthy check (not `!== 'Year'`) so this defaults to false while
  // periodStore hasn't loaded yet, rather than flashing "Scoped to FY26".
  const isScoped = $derived(
    periodStore.tree[periodState.code]?.periodType === 'Quarter' || periodStore.tree[periodState.code]?.periodType === 'Month'
  );
  // Derived from periodStore.tree on every read (see periodLabel), so a
  // deep-link arriving before periods have loaded shows the raw code only
  // momentarily — it corrects itself once periodStore is ready, rather than
  // freezing on the raw code (see docs/adr/0026).
  const scopedLabel = $derived(periodLabel(periodState.code));

  // Syncs the URL's ?period= into the shared periodState + refetches when it
  // differs — e.g. arriving via a Financial P&L cell deep-link
  // (see docs/adr/0026). Once vdtStore.tree reflects the requested period, its
  // nodes' actual/budget/priorYear are already scoped server-side — no
  // client-side re-derivation needed (contrast with the old getMonthlyNodeView).
  $effect(() => {
    if (periodCode && periodCode !== periodState.code) {
      periodState.set(periodCode);
      loadVdtScope(scopeState.code, periodCode);
    }
  });

  // vdtStore isn't populated by App.svelte's app-wide onMount (that's
  // glStore/Accounting only) — a deep-link straight into /vdt/:id needs its
  // own lazy trigger, same pattern VdtTree.svelte already uses.
  onMount(() => {
    if (vdtStore.status !== 'ready') loadVdtScope(scopeState.code, periodState.code);
  });

  const node = $derived(getNode(vdtStore.tree, params.id));
  const ancestors = $derived(
    node ? getAncestors(vdtStore.tree, node.id).map((a) => ({ id: a.id, name: a.name, href: `/vdt/${a.id}${periodQuery}` })) : []
  );
  // Real GL/FSI nodes carry no curated rank — every child ranks live by
  // contribution magnitude instead (see gl-client.ts rankChildren).
  const rankedChildren = $derived(node ? rankChildren(vdtStore.tree, node) : []);

</script>

{#if vdtStore.status === 'loading'}
  <PageHeader title="Value Driver" />
  <PageBody>Loading…</PageBody>
{:else if vdtStore.status === 'not-yet-modelled'}
  <PageHeader title="Value Driver" />
  <PageBody>
    <ContextBar />
    <NotYetModelled label="No GL data modelled for the selected company/BU yet." />
  </PageBody>
{:else if node}
  <PageHeader title={isScoped ? `${node.name} — ${scopedLabel}` : node.name} />
  <PageBody>
    <ContextBar {ancestors} />

    <div class="flex flex-col gap-4 pt-4">
    {#if isScoped}
      <div class="text-xs text-indigo-700 dark:text-indigo-300">
        Scoped to {scopedLabel} ·
        <a class="no-underline hover:underline" href="/vdt/{node.id}?period={DEFAULT_PERIOD_CODE}" use:link>view full year →</a>
      </div>
    {/if}
    <div class="border-[1.5px] border-gray-200 dark:border-gray-700 rounded-lg py-2.5 px-4 bg-white dark:bg-gray-800">
        {#if rankedChildren.length}
          <div class="hidden">Driver</div>
          <div class="flex flex-col">
            <div class="grid grid-cols-[1.4fr_0.6fr_0.6fr_0.5fr_0.8fr_0.5fr] items-center text-xs text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-700 pb-1">
              <span>Driver</span><span>Actual</span><span>Budget</span><span>Var%</span><span>Contribution</span><span>Rank</span>
            </div>
            {#each rankedChildren as child (child.id)}
              <a
                class="grid grid-cols-[1.4fr_0.6fr_0.6fr_0.5fr_0.8fr_0.5fr] items-center text-sm py-1 no-underline text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-900"
                href="/diagnostic/{child.id}"
                use:link
              >
                <span>▶ {child.name}</span>
                <span>{child.actual.toFixed(1)}</span>
                <span>{child.budget.toFixed(1)}</span>
                <span
                  class={child.direction === 'adverse'
                    ? 'text-red-600 dark:text-red-400'
                    : child.direction === 'favourable'
                      ? 'text-green-600 dark:text-green-400'
                      : ''}
                >
                  {formatVar(pct(child.actual, child.budget))}
                </span>
                <span>
                  {#if child.contributionWidthPct}
                    <div class="bg-red-600 dark:bg-red-400 h-2" style="width:{child.contributionWidthPct}%"></div>
                  {/if}
                </span>
                <span>{child.rank ? `#${child.rank}` : ''}</span>
              </a>
            {/each}
          </div>
          <div class="text-[10px] text-indigo-600 dark:text-indigo-400 mt-2">click row label → opens Driver Diagnostic · ranked by contribution to parent variance</div>
        {:else}
          <NotYetModelled
            label="No further decomposition modelled below {node.name}."
            linkHref="/diagnostic/{node.id}"
            linkLabel="Open Driver Diagnostic"
          />
        {/if}
    </div>

    {#if node.childIds.length}
      <div class="overflow-hidden border-[1.5px] border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800">
        <div class="flex items-center justify-between gap-4 border-b border-gray-200 dark:border-gray-700 px-4 py-2.5">
          <div class="text-xs text-gray-500 dark:text-gray-400">Decomposition tree</div>
          <div class="text-[10px] text-gray-500 dark:text-gray-400">
            Click a node with a ▶ marker to expand its children
          </div>
        </div>
        <div class="h-[34rem]">
          <ValueDriverFlow rootId={node.id} />
        </div>
      </div>
    {/if}

    <ChipRow label="Compare:" chips={['Petroleum', 'Gas', 'Offshore']} selected="Petroleum" />
    </div>
  </PageBody>
{:else}
  <PageHeader title="Unknown node" />
  <PageBody>Unknown node: {params.id}</PageBody>
{/if}
