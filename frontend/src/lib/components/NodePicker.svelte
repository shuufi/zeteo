<script lang="ts">
  import { glStore } from '../data/gl-store.svelte';
  import type { VdtNode } from '../data/types';

  let {
    value = $bindable<string | undefined>(undefined),
  }: { value?: string } = $props();

  let open = $state(false);
  let query = $state('');
  let rootEl = $state<HTMLDivElement | null>(null);

  // Only Reporting Root/Reporting Node can anchor a Comparison — a Posting GL
  // Account is always a leaf row, never bridgeable, even ones with Driver/
  // Driver Formula children (their units aren't RM-comparable) — see docs/adr/0031.
  const candidates = $derived(
    Object.values(glStore.tree)
      .filter((n) => n.nodeType === 'Reporting Root' || n.nodeType === 'Reporting Node')
      .sort((a, b) => a.name.localeCompare(b.name)),
  );

  const filtered = $derived(
    query.trim() === '' ? candidates : candidates.filter((n) => n.name.toLowerCase().includes(query.trim().toLowerCase())),
  );

  const selectedLabel = $derived(value ? (glStore.tree[value]?.name ?? value) : '');

  function select(node: VdtNode): void {
    value = node.id;
    query = '';
    open = false;
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

<div bind:this={rootEl}>
  <label for="comparison-node" class="block text-sm/6 font-medium text-gray-900 dark:text-white">Comparison node</label>
  <div class="relative mt-2">
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
        class="absolute z-20 mt-1 max-h-60 w-full overflow-auto rounded-md bg-white py-1 text-base shadow-lg outline-1 outline-black/5 sm:text-sm dark:bg-gray-800 dark:shadow-none dark:-outline-offset-1 dark:outline-white/10"
      >
        {#if filtered.length === 0}
          <div class="px-3 py-2 text-sm text-gray-500 dark:text-gray-400">No matching nodes.</div>
        {:else}
          {#each filtered as node (node.id)}
            <button
              type="button"
              onclick={() => select(node)}
              class="block w-full cursor-default px-3 py-2 text-left text-gray-900 select-none hover:bg-indigo-600 hover:text-white dark:text-white"
            >
              {node.name}
            </button>
          {/each}
        {/if}
      </div>
    {/if}
  </div>
</div>
