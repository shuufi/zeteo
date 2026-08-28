<script lang="ts">
  import { link } from 'svelte-spa-router';
  import PageHeader from '../lib/components/PageHeader.svelte';
  import PageBody from '../lib/components/PageBody.svelte';
  import ContextBar from '../lib/components/ContextBar.svelte';
  import { getNode, getAncestors, getChildren, formatVar } from '../lib/data/zeteo-data';

  const SHOW_MAX = 3;

  let { params }: { params: { id: string } } = $props();

  const node = $derived(getNode(params.id));
  const ancestors = $derived(node ? getAncestors(node.id).map((a) => ({ id: a.id, name: a.name, href: `/vdt/${a.id}` })) : []);
  const level1 = $derived(node ? getChildren(node) : []);
  const level1Shown = $derived(level1.slice(0, SHOW_MAX));
  const level1Hidden = $derived(Math.max(0, level1.length - SHOW_MAX));
  const selectedChild = $derived(level1.find((c) => c.childIds.length > 0));
  const level2 = $derived(selectedChild ? getChildren(selectedChild) : []);
  const level2Shown = $derived(level2.slice(0, SHOW_MAX));
  const level2Hidden = $derived(Math.max(0, level2.length - SHOW_MAX));
</script>

{#if node}
  <PageHeader title="{node.name} · Decomposition tree" />
  <PageBody>
    <ContextBar {ancestors} />

    <div class="flex flex-col gap-4 pt-4">
    <a
      class="self-start text-xs text-indigo-600 dark:text-indigo-400 no-underline hover:underline"
      href="/vdt/{node.id}"
      use:link
    >
      View as ranked list →
    </a>

    <div class="flex items-center gap-0 overflow-x-auto py-4">
      <div class="border-2 border-gray-900 dark:border-gray-50 rounded-lg py-2 px-2.5 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 min-w-[120px] flex flex-col gap-0.5 text-center">
        <b>{node.name}</b>
        <div
          class="text-[10px] {node.direction === 'adverse'
            ? 'text-red-600 dark:text-red-400'
            : node.direction === 'favourable'
              ? 'text-green-600 dark:text-green-400'
              : 'text-gray-500 dark:text-gray-400'}"
        >
          {formatVar(node.varPct)}
        </div>
      </div>

      {#if level1.length}
        <div class="w-8 h-0.5 bg-gray-900 dark:bg-gray-50 flex-none"></div>
        <div class="flex flex-col gap-2">
          {#each level1Shown as child (child.id)}
            <a
              class="rounded-lg py-2 px-2.5 no-underline text-gray-700 dark:text-gray-300 min-w-[150px] flex flex-col gap-0.5 hover:border-indigo-600 dark:hover:border-indigo-500 {child.id ===
              selectedChild?.id
                ? 'border-[1.5px] border-gray-900 dark:border-gray-50 bg-indigo-100 dark:bg-indigo-900'
                : 'border-[1.5px] border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800'}"
              href="/vdt-tree/{child.id}"
              use:link
            >
              <b>{child.name}</b>
              <span
                class="text-[10px] {child.direction === 'adverse'
                  ? 'text-red-600 dark:text-red-400'
                  : child.direction === 'favourable'
                    ? 'text-green-600 dark:text-green-400'
                    : 'text-gray-500 dark:text-gray-400'}"
              >
                {formatVar(child.varPct)}{child.id === selectedChild?.id ? ' · selected' : ''}
              </span>
            </a>
          {/each}
          {#if level1Hidden}
            <div class="border-[1.5px] border-dashed border-gray-200 dark:border-gray-700 rounded-lg py-2 px-2.5 bg-white dark:bg-gray-800 min-w-[150px] flex flex-col gap-0.5 text-gray-500 dark:text-gray-400 text-sm">
              +{level1Hidden} more ▾
            </div>
          {/if}
        </div>
      {/if}

      {#if level2.length}
        <div class="w-8 h-0.5 bg-gray-900 dark:bg-gray-50 flex-none"></div>
        <div class="flex flex-col gap-2">
          {#each level2Shown as child (child.id)}
            <a
              class="border-[1.5px] border-gray-200 dark:border-gray-700 rounded-lg py-2 px-2.5 bg-white dark:bg-gray-800 no-underline text-gray-700 dark:text-gray-300 min-w-[150px] flex flex-row justify-between items-center gap-0.5 hover:border-indigo-600 dark:hover:border-indigo-500 text-sm"
              href="/vdt-tree/{child.id}"
              use:link
            >
              {child.name}
              <span
                class="text-[10px] {child.direction === 'adverse'
                  ? 'text-red-600 dark:text-red-400'
                  : child.direction === 'favourable'
                    ? 'text-green-600 dark:text-green-400'
                    : 'text-gray-500 dark:text-gray-400'}"
              >
                {formatVar(child.varPct)}
              </span>
            </a>
          {/each}
          {#if level2Hidden}
            <div class="border-[1.5px] border-dashed border-gray-200 dark:border-gray-700 rounded-lg py-2 px-2.5 bg-white dark:bg-gray-800 min-w-[150px] flex flex-col gap-0.5 text-gray-500 dark:text-gray-400 text-sm">
              +{level2Hidden} more ▾
            </div>
          {/if}
        </div>
      {/if}
    </div>

    <p class="text-xs text-gray-500 dark:text-gray-400">
      only two levels expanded at once — siblings collapse to "+N more"
    </p>

    <div>
      <a
        class="text-sm text-indigo-600 dark:text-indigo-400 no-underline font-semibold hover:underline"
        href="/diagnostic/{selectedChild ? selectedChild.id : node.id}"
        use:link
      >
        Open Driver Diagnostic for {selectedChild ? selectedChild.name : node.name} →
      </a>
    </div>
    </div>
  </PageBody>
{:else}
  <PageHeader title="Unknown node" />
  <PageBody>Unknown node: {params.id}</PageBody>
{/if}
