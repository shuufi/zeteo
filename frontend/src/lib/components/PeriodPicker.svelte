<script lang="ts">
  import type { PeriodNode } from '../data/types';
  import { periodDraft } from '../state/period-draft.svelte';
  import { periodStore, loadPeriods, periodLabel } from '../data/period-store.svelte';

  loadPeriods();

  let open = $state(false);
  // Which non-leaf periods are expanded to show their children — a plain
  // accordion, not a search/autocomplete (Year/Quarter/Month codes don't
  // share text with each other, so filter-as-you-type hid everything but
  // whatever was already selected — see docs/adr/0026).
  let expanded = $state(new Set<string>());
  let rootEl = $state<HTMLDivElement | null>(null);

  const year = $derived(Object.values(periodStore.tree).find((p) => p.parentId === null));

  function childrenOf(node: PeriodNode): PeriodNode[] {
    return node.childIds.map((id) => periodStore.tree[id]).filter((p): p is PeriodNode => p !== undefined);
  }

  // Stages the pick as a draft only — ContextBar's Apply button is what
  // actually commits it to periodState and refetches (see docs/adr/0027).
  function select(period: PeriodNode): void {
    periodDraft.set(period.id);
    if (period.childIds.length === 0) {
      open = false;
      return;
    }
    const next = new Set(expanded);
    if (next.has(period.id)) next.delete(period.id);
    else next.add(period.id);
    expanded = next;
  }

  $effect(() => {
    if (!open) return;
    function handlePointerDown(e: PointerEvent): void {
      if (rootEl && !rootEl.contains(e.target as Node)) open = false;
    }
    function handleKeydown(e: KeyboardEvent): void {
      if (e.key === 'Escape') open = false;
    }
    document.addEventListener('pointerdown', handlePointerDown);
    document.addEventListener('keydown', handleKeydown);
    return () => {
      document.removeEventListener('pointerdown', handlePointerDown);
      document.removeEventListener('keydown', handleKeydown);
    };
  });
</script>

{#snippet row(period: PeriodNode, depth: number)}
  <button
    type="button"
    onclick={() => select(period)}
    style="padding-left: {depth * 14 + 8}px"
    class="flex w-full items-center gap-1.5 py-1.5 pr-3 text-left text-sm select-none {period.id === periodDraft.code
      ? 'bg-indigo-600 text-white'
      : 'text-gray-900 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700'}"
  >
    {#if period.childIds.length}
      <svg
        viewBox="0 0 20 20"
        fill="currentColor"
        aria-hidden="true"
        class="size-4 shrink-0 transition-transform {period.id === periodDraft.code ? 'text-white' : 'text-gray-400 dark:text-gray-500'} {expanded.has(
          period.id
        )
          ? 'rotate-90'
          : ''}"
      >
        <path
          fill-rule="evenodd"
          d="M7.21 14.77a.75.75 0 0 1 .02-1.06L11.168 10 7.23 6.29a.75.75 0 1 1 1.04-1.08l4.5 4.25a.75.75 0 0 1 0 1.08l-4.5 4.25a.75.75 0 0 1-1.06-.02Z"
          clip-rule="evenodd"
        />
      </svg>
    {:else}
      <span class="inline-block size-4 shrink-0"></span>
    {/if}
    <span class="truncate">{period.label}</span>
  </button>
  {#if expanded.has(period.id)}
    {#each childrenOf(period) as child (child.id)}
      {@render row(child, depth + 1)}
    {/each}
  {/if}
{/snippet}

<div class="flex items-center gap-1.5" bind:this={rootEl}>
  <span class="text-xs whitespace-nowrap text-gray-500 dark:text-gray-400">Period:</span>

  <div class="relative">
    <button
      type="button"
      onclick={() => (open = !open)}
      class="grid min-w-28 cursor-default grid-cols-1 rounded-md bg-white py-1.5 pr-2 pl-3 text-left text-gray-900 outline-1 -outline-offset-1 outline-gray-300 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-indigo-600 sm:text-sm/6 dark:bg-white/5 dark:text-white dark:outline-white/10 dark:focus-visible:outline-indigo-500"
    >
      <span class="col-start-1 row-start-1 truncate pr-6">{periodLabel(periodDraft.code)}</span>
      <svg
        viewBox="0 0 16 16"
        fill="currentColor"
        aria-hidden="true"
        class="col-start-1 row-start-1 size-5 self-center justify-self-end text-gray-500 sm:size-4 dark:text-gray-400"
      >
        <path
          fill-rule="evenodd"
          d="M5.22 10.22a.75.75 0 0 1 1.06 0L8 11.94l1.72-1.72a.75.75 0 1 1 1.06 1.06l-2.25 2.25a.75.75 0 0 1-1.06 0l-2.25-2.25a.75.75 0 0 1 0-1.06ZM10.78 5.78a.75.75 0 0 1-1.06 0L8 4.06 6.28 5.78a.75.75 0 0 1-1.06-1.06l2.25-2.25a.75.75 0 0 1 1.06 0l2.25 2.25a.75.75 0 0 1 0 1.06Z"
          clip-rule="evenodd"
        />
      </svg>
    </button>

    {#if open}
      <div
        class="absolute z-10 mt-1 max-h-72 w-48 overflow-auto rounded-md bg-white py-1 shadow-lg outline-1 outline-black/5 dark:bg-gray-800 dark:shadow-none dark:-outline-offset-1 dark:outline-white/10"
      >
        {#if periodStore.status === 'loading'}
          <div class="px-3 py-2 text-sm text-gray-500 dark:text-gray-400">Loading…</div>
        {:else if periodStore.status === 'error'}
          <div class="px-3 py-2 text-sm text-gray-500 dark:text-gray-400">
            Couldn't load periods.
            <button type="button" class="ml-2 cursor-pointer border-0 bg-transparent p-0 text-indigo-600 underline dark:text-indigo-400" onclick={loadPeriods}>Retry</button>
          </div>
        {:else if year}
          {@render row(year, 0)}
        {/if}
      </div>
    {/if}
  </div>
</div>
