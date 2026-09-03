<script lang="ts">
  import { onMount } from 'svelte';
  import ValueDriverFlow from '../lib/components/ValueDriverFlow.svelte';
  import { vdtStore, loadVdtScope } from '../lib/data/vdt-store.svelte';
  import { scopeState } from '../lib/state/scope.svelte';

  let { params }: { params: { id?: string } } = $props();
  const rootId = $derived(params.id ?? 'NPAT');

  onMount(() => {
    if (vdtStore.status !== 'ready') loadVdtScope(scopeState.code);
  });
</script>

<div class="shell py-4">
  <h1 class="mb-2 text-lg font-semibold text-gray-900 dark:text-white">
    Value Driver Tree
  </h1>
  <p class="mb-4 text-sm text-gray-500 dark:text-gray-400">
    Rooted at <code>{rootId}</code>. Click a node with a ▶ marker to expand its children.
  </p>
</div>

<div style="height: calc(100vh - 10rem);">
  {#if vdtStore.status === 'ready'}
    <ValueDriverFlow {rootId} />
  {:else if vdtStore.status === 'loading'}
    <p class="shell text-sm text-gray-500">Loading VDT tree…</p>
  {:else}
    <p class="shell text-sm text-red-600">Failed to load VDT tree ({vdtStore.status}).</p>
  {/if}
</div>
