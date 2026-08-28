<script lang="ts">
  import { link, router } from 'svelte-spa-router';
  import PageHeader from '../lib/components/PageHeader.svelte';
  import PageBody from '../lib/components/PageBody.svelte';
  import ContextBar from '../lib/components/ContextBar.svelte';
  import Sparkline from '../lib/components/Sparkline.svelte';
  import ChipRow from '../lib/components/ChipRow.svelte';
  import NotYetModelled from '../lib/components/NotYetModelled.svelte';
  import {
    getNode,
    getAncestors,
    getChildren,
    getMonthlyNodeView,
    getMonthlyChildren,
    months,
    formatRm,
    formatVar,
  } from '../lib/data/zeteo-data';

  let { params }: { params: { id: string } } = $props();

  const monthIndex = $derived(months.indexOf(new URLSearchParams(router.querystring ?? '').get('month') ?? ''));
  const selectedMonth = $derived(monthIndex >= 0 ? months[monthIndex] : null);
  const monthQuery = $derived(selectedMonth ? `?month=${selectedMonth}` : '');

  const baseNode = $derived(getNode(params.id));
  const node = $derived(
    baseNode && selectedMonth ? (getMonthlyNodeView(baseNode.id, monthIndex) ?? baseNode) : baseNode
  );
  const ancestors = $derived(
    node ? getAncestors(node.id).map((a) => ({ id: a.id, name: a.name, href: `/vdt/${a.id}${monthQuery}` })) : []
  );
  // Rank by explicit `rank` where set, else fall back to contribution magnitude —
  // every child renders in the table, not just ones a prior mock happened to rank.
  const rankedChildren = $derived(
    node
      ? selectedMonth
        ? getMonthlyChildren(node, monthIndex)
        : [...getChildren(node)].sort((a, b) => {
            if (a.rank !== undefined && b.rank !== undefined) return a.rank - b.rank;
            if (a.rank !== undefined) return -1;
            if (b.rank !== undefined) return 1;
            return Math.abs(b.actual - b.budget) - Math.abs(a.actual - a.budget);
          })
      : []
  );
</script>

{#if node}
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
        <div class="font-black text-2xl text-gray-900 dark:text-gray-50">{formatRm(node.actual)}</div>
        <div class="text-xs text-red-600 dark:text-red-400">vs Budget {formatRm(node.budget)} · {formatVar(node.varPct)}</div>
        {#if node.priorYear !== undefined}
          <div class="text-xs text-gray-500 dark:text-gray-400 mt-1">Prior year: {formatRm(node.priorYear)}</div>
        {/if}
        {#if node.trend?.length}
          <div class="mt-2.5 border-b-[1.5px] border-gray-200 dark:border-gray-700">
            <Sparkline points={node.trend} width={180} height={30} />
          </div>
          <div class="text-[10px] text-gray-500 dark:text-gray-400">trend, {node.trend.length} periods</div>
        {/if}
        <a class="block mt-4 text-xs text-indigo-600 dark:text-indigo-400 no-underline hover:underline" href="/vdt-tree/{node.id}" use:link>View as decomposition tree →</a>
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
                  {formatVar(child.varPct)}
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

    <ChipRow label="Compare:" chips={['Petroleum', 'Gas', 'Offshore']} selected="Petroleum" />
    </div>
  </PageBody>
{:else}
  <PageHeader title="Unknown node" />
  <PageBody>Unknown node: {params.id}</PageBody>
{/if}
