<script lang="ts">
  import { glStore } from '../data/gl-store.svelte';
  import type { VdtNode } from '../data/types';

  let {
    value = $bindable<string | undefined>(undefined),
  }: { value?: string } = $props();

  let open = $state(false);
  let query = $state('');
  let rootEl = $state<HTMLDivElement | null>(null);
  // Which Reporting Node rows are expanded to show their children — same
  // accordion concept as BusinessPicker/PeriodPicker.
  let expanded = $state(new Set<string>());

  // Only Reporting Root/Reporting Node can anchor a Comparison — a Posting GL
  // Account is always a leaf row, never bridgeable, even ones with Driver/
  // Driver Formula children (their units aren't RM-comparable) — see docs/adr/0031.
  const candidates = $derived(
    Object.values(glStore.tree).filter((n) => n.nodeType === 'Reporting Root' || n.nodeType === 'Reporting Node'),
  );
  const nodeById = $derived(new Map(candidates.map((n) => [n.id, n])));
  const root = $derived(candidates.find((n) => n.parentId === null));

  function childrenOf(node: VdtNode): VdtNode[] {
    return node.childIds.map((id) => nodeById.get(id)).filter((n): n is VdtNode => n !== undefined);
  }

  function ancestorsOf(id: string): string[] {
    const chain: string[] = [];
    let current = nodeById.get(id);
    while (current?.parentId) {
      chain.push(current.parentId);
      current = nodeById.get(current.parentId);
    }
    return chain;
  }

  const trimmedQuery = $derived(query.trim().toLowerCase());
  const matchIds = $derived(
    trimmedQuery === '' ? new Set<string>() : new Set(candidates.filter((n) => n.name.toLowerCase().includes(trimmedQuery)).map((n) => n.id)),
  );
  // While searching, every ancestor of a match auto-expands (and stays
  // visible) so the match's position in the hierarchy is shown, not just its
  // name — pruning branches with no match keeps the list from being the
  // full ~88-node tree on every keystroke.
  const ancestorIds = $derived.by(() => {
    const ids = new Set<string>();
    for (const id of matchIds) for (const a of ancestorsOf(id)) ids.add(a);
    return ids;
  });
  const searching = $derived(trimmedQuery !== '');

  function isVisible(node: VdtNode): boolean {
    return !searching || matchIds.has(node.id) || ancestorIds.has(node.id);
  }

  function isExpanded(node: VdtNode): boolean {
    return searching ? ancestorIds.has(node.id) : expanded.has(node.id);
  }

  const selectedLabel = $derived(value ? (glStore.tree[value]?.name ?? value) : '');

  function select(node: VdtNode): void {
    value = node.id;
    query = '';
    const children = childrenOf(node);
    if (children.length === 0) {
      open = false;
      return;
    }
    const next = new Set(expanded);
    for (const a of ancestorsOf(node.id)) next.add(a);
    if (next.has(node.id)) next.delete(node.id);
    else next.add(node.id);
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

{#snippet row(node: VdtNode, depth: number)}
  {#if isVisible(node)}
    {@const children = childrenOf(node)}
    <button
      type="button"
      onclick={() => select(node)}
      style="padding-left: {depth * 14 + 12}px"
      class="flex w-full items-center gap-1.5 py-1.5 pr-3 text-left text-sm select-none {node.id === value
        ? 'bg-indigo-600 text-white'
        : 'text-gray-900 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700'}"
    >
      {#if children.length}
        <svg
          viewBox="0 0 20 20"
          fill="currentColor"
          aria-hidden="true"
          class="size-4 shrink-0 transition-transform {node.id === value ? 'text-white' : 'text-gray-400 dark:text-gray-500'} {isExpanded(node)
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
      <span class="truncate">{node.name}</span>
    </button>
    {#if isExpanded(node)}
      {#each children as child (child.id)}
        {@render row(child, depth + 1)}
      {/each}
    {/if}
  {/if}
{/snippet}

<div class="flex items-center gap-1.5" bind:this={rootEl}>
  <span class="text-xs whitespace-nowrap text-gray-500 dark:text-gray-400">Node:</span>
  <div class="relative w-64">
    <input
      id="comparison-node"
      type="text"
      placeholder="Search NPAT, Revenue, Manpower Cost…"
      value={open ? query : selectedLabel}
      onfocus={() => (open = true)}
      oninput={(e) => (query = (e.target as HTMLInputElement).value)}
      class="block w-full rounded-md bg-white py-1.5 pr-3 pl-3 text-base text-gray-900 outline-1 -outline-offset-1 outline-gray-300 placeholder:text-gray-400 focus:outline-2 focus:-outline-offset-2 focus:outline-indigo-600 sm:text-sm/6 dark:bg-white/5 dark:text-white dark:outline-white/10 dark:placeholder:text-gray-500 dark:focus:outline-indigo-500"
    />

    {#if open}
      <div
        class="absolute z-20 mt-1 max-h-72 w-[28rem] overflow-auto rounded-md bg-white py-1 text-base shadow-lg outline-1 outline-black/5 sm:text-sm dark:bg-gray-800 dark:shadow-none dark:-outline-offset-1 dark:outline-white/10"
      >
        {#if root}
          {@render row(root, 0)}
          {#if searching && matchIds.size === 0}
            <div class="px-3 py-2 text-sm text-gray-500 dark:text-gray-400">No matching nodes.</div>
          {/if}
        {/if}
      </div>
    {/if}
  </div>
</div>
