<script lang="ts">
  import type { CompanyNode } from '../data/types';
  import { scopeState } from '../state/scope.svelte';
  import { scopeDraft } from '../state/scope-draft.svelte';
  import { periodState } from '../state/period.svelte';
  import { companyStore, loadCompanies } from '../data/company-store.svelte';
  import { loadScope } from '../data/gl-store.svelte';

  let open = $state(false);
  let query = $state('');
  // Which Group/BU rows are expanded to show their children — same accordion
  // concept as PeriodPicker/NodePicker.
  let expanded = $state(new Set<string>());
  let rootEl = $state<HTMLDivElement | null>(null);
  let defaulted = false;

  loadCompanies();

  const group = $derived(Object.values(companyStore.tree).find((n) => n.parentId === null));

  function childrenOf(node: CompanyNode): CompanyNode[] {
    return node.childIds.map((id) => companyStore.tree[id]).filter((n): n is CompanyNode => n !== undefined);
  }

  function ancestorsOf(id: string): string[] {
    const chain: string[] = [];
    let current = companyStore.tree[id];
    while (current?.parentId) {
      chain.push(current.parentId);
      current = companyStore.tree[current.parentId];
    }
    return chain;
  }

  const trimmedQuery = $derived(query.trim().toLowerCase());
  const searching = $derived(trimmedQuery !== '');
  const matchIds = $derived(
    trimmedQuery === ''
      ? new Set<string>()
      : new Set(
          Object.values(companyStore.tree)
            .filter((n) => n.label.toLowerCase().includes(trimmedQuery) || n.id.toLowerCase().includes(trimmedQuery))
            .map((n) => n.id),
        ),
  );
  // While searching, every ancestor of a match auto-expands (and stays
  // visible) so the match's position in the hierarchy is shown, not just its
  // name — pruning branches with no match keeps the list from being the
  // full company tree on every keystroke (see docs/adr/0031's NodePicker).
  const ancestorIds = $derived.by(() => {
    const ids = new Set<string>();
    for (const id of matchIds) for (const a of ancestorsOf(id)) ids.add(a);
    return ids;
  });

  function isVisible(node: CompanyNode): boolean {
    return !searching || matchIds.has(node.id) || ancestorIds.has(node.id);
  }

  function isExpanded(node: CompanyNode): boolean {
    return searching ? ancestorIds.has(node.id) : expanded.has(node.id);
  }

  // Establishes the initial applied scope — not a user picking a dropdown
  // option, so this commits immediately rather than staging a draft (see
  // docs/adr/0027).
  $effect(() => {
    if (defaulted || companyStore.status !== 'ready' || !group) return;
    defaulted = true;
    // scopeState's default can be any node in the hierarchy (a Company, not
    // just a top-level BU — see docs/adr/0032) — only fall back to the first
    // BU if that default doesn't actually exist in the loaded tree.
    const fallback = companyStore.tree[scopeState.code] ?? childrenOf(group)[0];
    if (fallback && fallback.id !== scopeState.code) {
      scopeState.set(fallback.id, fallback.label);
      loadScope(fallback.id, periodState.code);
    }
  });

  // Stages the pick as a draft only — ContextBar's Apply button is what
  // actually commits it to scopeState and refetches (see docs/adr/0027).
  function select(node: CompanyNode): void {
    scopeDraft.set(node.id, node.label);
    query = '';
    if (node.childIds.length === 0) {
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

{#snippet row(node: CompanyNode, depth: number)}
  {#if isVisible(node)}
    {@const children = childrenOf(node)}
    <button
      type="button"
      onclick={() => select(node)}
      style="padding-left: {depth * 14 + 12}px"
      class="flex w-full items-center gap-1.5 py-1.5 pr-3 text-left text-sm select-none {node.companyType !== 'Company' ? 'font-semibold' : ''} {node.id ===
      scopeDraft.code
        ? 'bg-indigo-600 text-white'
        : 'text-gray-900 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700'}"
    >
      {#if children.length}
        <svg
          viewBox="0 0 20 20"
          fill="currentColor"
          aria-hidden="true"
          class="size-4 shrink-0 transition-transform {node.id === scopeDraft.code ? 'text-white' : 'text-gray-400 dark:text-gray-500'} {isExpanded(node)
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
      <span class="truncate">{node.companyType === 'Company' ? `${node.id} ${node.label}` : node.label}</span>
    </button>
    {#if isExpanded(node)}
      {#each children as child (child.id)}
        {@render row(child, depth + 1)}
      {/each}
    {/if}
  {/if}
{/snippet}

<div class="flex items-center gap-1.5" bind:this={rootEl}>
  <span class="text-xs whitespace-nowrap text-gray-500 dark:text-gray-400">Company:</span>

  <div class="relative w-48">
    <input
      id="business-picker"
      type="text"
      placeholder="Search AET, OBU, a company…"
      value={open ? query : scopeDraft.label}
      onfocus={() => (open = true)}
      oninput={(e) => (query = (e.target as HTMLInputElement).value)}
      class="block w-full rounded-md bg-white py-1.5 pr-3 pl-3 text-gray-900 outline-1 -outline-offset-1 outline-gray-300 placeholder:text-gray-400 focus:outline-2 focus:-outline-offset-2 focus:outline-indigo-600 sm:text-sm/6 dark:bg-white/5 dark:text-white dark:outline-white/10 dark:placeholder:text-gray-500 dark:focus:outline-indigo-500"
    />

    {#if open}
      <div
        class="absolute z-20 mt-1 max-h-72 w-[28rem] overflow-auto rounded-md bg-white py-1 shadow-lg outline-1 outline-black/5 dark:bg-gray-800 dark:shadow-none dark:-outline-offset-1 dark:outline-white/10"
      >
        {#if companyStore.status === 'loading'}
          <div class="px-3 py-2 text-sm text-gray-500 dark:text-gray-400">Loading…</div>
        {:else if companyStore.status === 'error'}
          <div class="px-3 py-2 text-sm text-gray-500 dark:text-gray-400">
            Couldn't load companies.
            <button type="button" class="ml-2 cursor-pointer border-0 bg-transparent p-0 text-indigo-600 underline dark:text-indigo-400" onclick={loadCompanies}>Retry</button>
          </div>
        {:else if group}
          {@render row(group, 0)}
          {#if searching && matchIds.size === 0}
            <div class="px-3 py-2 text-sm text-gray-500 dark:text-gray-400">No matching companies.</div>
          {/if}
        {/if}
      </div>
    {/if}
  </div>
</div>
