<script lang="ts">
  import { link, router } from 'svelte-spa-router';
  import PageHeader from '../lib/components/PageHeader.svelte';
  import PageBody from '../lib/components/PageBody.svelte';
  import ContextBar from '../lib/components/ContextBar.svelte';
  import Sparkline from '../lib/components/Sparkline.svelte';
  import ChipRow from '../lib/components/ChipRow.svelte';
  import NotYetModelled from '../lib/components/NotYetModelled.svelte';
  import { glStore } from '../lib/data/gl-store.svelte';
  import { getNode, getAncestors, getChildren, getMonthlyNodeView, rankChildren } from '../lib/data/gl-client';
  import { months, formatRm, formatVar, pct } from '../lib/data/format';

  const TREE_SHOW_MAX = 3;

  let { params }: { params: { id: string } } = $props();

  const monthIndex = $derived(months.indexOf(new URLSearchParams(router.querystring ?? '').get('month') ?? ''));
  const selectedMonth = $derived(monthIndex >= 0 ? months[monthIndex] : null);
  const monthQuery = $derived(selectedMonth ? `?month=${selectedMonth}` : '');

  const baseNode = $derived(getNode(glStore.tree, params.id));
  const node = $derived(
    baseNode && selectedMonth ? (getMonthlyNodeView(glStore.tree, baseNode.id, monthIndex) ?? baseNode) : baseNode
  );
  const ancestors = $derived(
    node ? getAncestors(glStore.tree, node.id).map((a) => ({ id: a.id, name: a.name, href: `/vdt/${a.id}${monthQuery}` })) : []
  );
  // Real GL/FSI nodes carry no curated rank — every child ranks live by
  // contribution magnitude instead (see gl-client.ts rankChildren).
  const rankedChildren = $derived(node ? rankChildren(glStore.tree, node, selectedMonth ? monthIndex : null) : []);

  // Decomposition tree preview under the ranked list, two levels deep,
  // scoped to the selected month.
  const scopeMonthly = (n: import('../lib/data/types').VdtNode) =>
    selectedMonth ? (getMonthlyNodeView(glStore.tree, n.id, monthIndex) ?? n) : n;
  const treeLevel1 = $derived(
    node
      ? getChildren(glStore.tree, node)
          .filter((c) => c.nodeType !== 'Operational Driver')
          .map(scopeMonthly)
      : []
  );
  const treeLevel1Shown = $derived(treeLevel1.slice(0, TREE_SHOW_MAX));
  const treeLevel1Hidden = $derived(Math.max(0, treeLevel1.length - TREE_SHOW_MAX));
  const treeSelectedChild = $derived(treeLevel1.find((c) => c.childIds.length > 0));
  const treeLevel2 = $derived(
    treeSelectedChild
      ? getChildren(glStore.tree, treeSelectedChild)
          .filter((c) => c.nodeType !== 'Operational Driver')
          .map(scopeMonthly)
      : []
  );
  const treeLevel2Shown = $derived(treeLevel2.slice(0, TREE_SHOW_MAX));
  const treeLevel2Hidden = $derived(Math.max(0, treeLevel2.length - TREE_SHOW_MAX));
</script>

{#if glStore.status === 'loading'}
  <PageHeader title="Value Driver" />
  <PageBody>Loading…</PageBody>
{:else if glStore.status === 'not-yet-modelled'}
  <PageHeader title="Value Driver" />
  <PageBody>
    <ContextBar />
    <NotYetModelled label="No GL data modelled for the selected company/BU yet." />
  </PageBody>
{:else if node}
  <PageHeader title={selectedMonth ? `${node.name} — ${selectedMonth}` : node.name} />
  <PageBody>
    <ContextBar {ancestors} />

    <div class="flex flex-col gap-4 pt-4">
    {#if selectedMonth}
      <div class="text-xs text-indigo-700 dark:text-indigo-300">
        Scoped to {selectedMonth} ·
        <a class="no-underline hover:underline" href="/vdt/{node.id}" use:link>view full year →</a>
      </div>
    {/if}
    <div class="flex gap-4">
      <div class="w-60 flex-none border-2 border-gray-900 dark:border-gray-50 rounded-lg p-4 bg-white dark:bg-gray-800">
        <div class="text-xs text-gray-500 dark:text-gray-400">{node.name}</div>
        <div class="font-black text-2xl text-gray-900 dark:text-gray-50">{formatRm(Math.abs(node.actual))}</div>
        <div class="text-xs text-red-600 dark:text-red-400">vs Budget {formatRm(Math.abs(node.budget))} · {formatVar(pct(node.actual, node.budget))}</div>
        {#if node.priorYear !== undefined}
          <div class="text-xs text-gray-500 dark:text-gray-400 mt-1">Prior year: {formatRm(Math.abs(node.priorYear))}</div>
        {/if}
        {#if node.monthlyActual.length}
          <div class="mt-2.5 border-b-[1.5px] border-gray-200 dark:border-gray-700">
            <Sparkline points={node.monthlyActual} width={180} height={30} />
          </div>
          <div class="text-[10px] text-gray-500 dark:text-gray-400">trend, {node.monthlyActual.length} periods</div>
        {/if}
      </div>

      <div class="flex-1 border-[1.5px] border-gray-200 dark:border-gray-700 rounded-lg py-2.5 px-4 bg-white dark:bg-gray-800">
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
    </div>

    {#if treeLevel1.length}
      <div class="border-[1.5px] border-gray-200 dark:border-gray-700 rounded-lg py-2.5 px-4 bg-white dark:bg-gray-800">
        <div class="text-xs text-gray-500 dark:text-gray-400 mb-2">Decomposition tree</div>

        <div class="flex items-center gap-0 overflow-x-auto py-2">
          <div class="border-2 border-gray-900 dark:border-gray-50 rounded-lg py-2 px-2.5 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 min-w-[120px] flex flex-col gap-0.5 text-center">
            <b>{node.name}</b>
            <div
              class="text-[10px] {node.direction === 'adverse'
                ? 'text-red-600 dark:text-red-400'
                : node.direction === 'favourable'
                  ? 'text-green-600 dark:text-green-400'
                  : 'text-gray-500 dark:text-gray-400'}"
            >
              {formatVar(pct(node.actual, node.budget))}
            </div>
          </div>

          <div class="w-8 h-0.5 bg-gray-900 dark:bg-gray-50 flex-none"></div>
          <div class="flex flex-col gap-2">
            {#each treeLevel1Shown as child (child.id)}
              <div
                class="rounded-lg py-2 px-2.5 text-gray-700 dark:text-gray-300 min-w-[150px] flex flex-col gap-0.5 {child.id ===
                treeSelectedChild?.id
                  ? 'border-[1.5px] border-gray-900 dark:border-gray-50 bg-indigo-100 dark:bg-indigo-900'
                  : 'border-[1.5px] border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800'}"
              >
                <b>{child.name}</b>
                <span
                  class="text-[10px] {child.direction === 'adverse'
                    ? 'text-red-600 dark:text-red-400'
                    : child.direction === 'favourable'
                      ? 'text-green-600 dark:text-green-400'
                      : 'text-gray-500 dark:text-gray-400'}"
                >
                  {formatVar(pct(child.actual, child.budget))}{child.id === treeSelectedChild?.id ? ' · selected' : ''}
                </span>
              </div>
            {/each}
            {#if treeLevel1Hidden}
              <div class="border-[1.5px] border-dashed border-gray-200 dark:border-gray-700 rounded-lg py-2 px-2.5 bg-white dark:bg-gray-800 min-w-[150px] flex flex-col gap-0.5 text-gray-500 dark:text-gray-400 text-sm">
                +{treeLevel1Hidden} more ▾
              </div>
            {/if}
          </div>

          {#if treeLevel2.length}
            <div class="w-8 h-0.5 bg-gray-900 dark:bg-gray-50 flex-none"></div>
            <div class="flex flex-col gap-2">
              {#each treeLevel2Shown as child (child.id)}
                <div
                  class="border-[1.5px] border-gray-200 dark:border-gray-700 rounded-lg py-2 px-2.5 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 min-w-[150px] flex flex-row justify-between items-center gap-0.5 text-sm"
                >
                  {child.name}
                  <span
                    class="text-[10px] {child.direction === 'adverse'
                      ? 'text-red-600 dark:text-red-400'
                      : child.direction === 'favourable'
                        ? 'text-green-600 dark:text-green-400'
                        : 'text-gray-500 dark:text-gray-400'}"
                  >
                    {formatVar(pct(child.actual, child.budget))}
                  </span>
                </div>
              {/each}
              {#if treeLevel2Hidden}
                <div class="border-[1.5px] border-dashed border-gray-200 dark:border-gray-700 rounded-lg py-2 px-2.5 bg-white dark:bg-gray-800 min-w-[150px] flex flex-col gap-0.5 text-gray-500 dark:text-gray-400 text-sm">
                  +{treeLevel2Hidden} more ▾
                </div>
              {/if}
            </div>
          {/if}
        </div>

        <p class="text-[10px] text-gray-500 dark:text-gray-400">only two levels expanded at once — siblings collapse to "+N more"</p>
      </div>
    {/if}

    <ChipRow label="Compare:" chips={['Petroleum', 'Gas', 'Offshore']} selected="Petroleum" />
    </div>
  </PageBody>
{:else}
  <PageHeader title="Unknown node" />
  <PageBody>Unknown node: {params.id}</PageBody>
{/if}
