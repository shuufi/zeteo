<script lang="ts">
  import { onMount } from 'svelte';
  import PageHeader from '../lib/components/PageHeader.svelte';
  import PageBody from '../lib/components/PageBody.svelte';
  import ContextBar from '../lib/components/ContextBar.svelte';
  import ValueDriverFlow from '../lib/components/ValueDriverFlow.svelte';
  import { vdtStore, loadVdtScope } from '../lib/data/vdt-store.svelte';
  import { scopeState } from '../lib/state/scope.svelte';
  import { periodState } from '../lib/state/period.svelte';
  import { hierarchyMoneyValues, resolveMoneyScale, type MoneyScaleChoice } from '../lib/data/format';

  let { params }: { params: { id?: string } } = $props();
  const rootId = $derived(params.id ?? 'NPAT');
  let moneyScale = $state<MoneyScaleChoice>('auto');
  const moneyValues = $derived(hierarchyMoneyValues(vdtStore.tree, rootId));
  const resolvedMoneyScale = $derived(resolveMoneyScale(moneyScale, moneyValues));
  const currency = $derived(vdtStore.meta?.currency ?? '');

  let lastScaleRoot = '';
  $effect(() => {
    if (lastScaleRoot && rootId !== lastScaleRoot) moneyScale = 'auto';
    lastScaleRoot = rootId;
  });

  onMount(() => {
    if (vdtStore.status !== 'ready') loadVdtScope(scopeState.code, periodState.code);
  });
</script>

<PageHeader title="Value Driver Tree" />
<PageBody>
  <ContextBar showMoneyScale {currency} {moneyValues} bind:moneyScale />
  <p class="py-3 text-sm text-gray-500 dark:text-gray-400">
    Rooted at <code>{rootId}</code>. Click a node with a ▶ marker to expand its children.
  </p>
  <div style="height: calc(100vh - 14rem);">
  {#if vdtStore.status === 'ready'}
    <ValueDriverFlow {rootId} {currency} moneyScale={resolvedMoneyScale} />
  {:else if vdtStore.status === 'loading'}
    <p class="text-sm text-gray-500">Loading VDT tree…</p>
  {:else}
    <p class="text-sm text-red-600">Failed to load VDT tree ({vdtStore.status}).</p>
  {/if}
  </div>
</PageBody>
