<script lang="ts">
  import { onMount } from 'svelte';
  import { SvelteFlow, Background, Controls, MiniMap, Position, type Node, type Edge } from '@xyflow/svelte';
  import '@xyflow/svelte/dist/style.css';
  import { stratify, tree as d3tree } from 'd3-hierarchy';
  import { glStore, loadScope } from '../lib/data/gl-store.svelte';
  import { scopeState } from '../lib/state/scope.svelte';
  import type { VdtNode } from '../lib/data/types';

  const NODE_WIDTH = 220;
  const NODE_HEIGHT = 60;
  const LEVEL_GAP = 100;
  const SIBLING_GAP = 20;

  let { params }: { params: { id?: string } } = $props();
  const rootId = $derived(params.id ?? 'NPAT');

  // Root itself starts expanded (so its direct children show); nothing
  // deeper is expanded until the user clicks a node that has children.
  let expandedIds = $state(new Set<string>());
  let lastRootId = '';

  $effect(() => {
    if (rootId !== lastRootId) {
      lastRootId = rootId;
      expandedIds = new Set([rootId]);
    }
  });

  function toggle(id: string) {
    const next = new Set(expandedIds);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    expandedIds = next;
  }

  // Walk down from rootId, only descending into a node's children once
  // that node has been expanded — everything else stays collapsed.
  function visibleSubtree(tree: Record<string, VdtNode>, root: string, expanded: Set<string>): VdtNode[] {
    const out: VdtNode[] = [];
    const queue = [root];
    while (queue.length) {
      const id = queue.shift()!;
      const n = tree[id];
      if (!n) continue;
      out.push(n);
      if (expanded.has(id)) queue.push(...n.childIds);
    }
    return out;
  }

  let nodes = $state<Node[]>([]);
  let edges = $state<Edge[]>([]);

  onMount(() => {
    if (glStore.status !== 'ready') loadScope(scopeState.code);
  });

  $effect(() => {
    if (glStore.status !== 'ready') return;
    const tree = glStore.tree;
    if (!tree[rootId]) return;

    const visible = visibleSubtree(tree, rootId, expandedIds);

    const root = stratify<VdtNode>()
      .id((d) => d.id)
      .parentId((d) => (d.id === rootId ? undefined : (d.parentId ?? undefined)))(visible);

    const layout = d3tree<VdtNode>().nodeSize([NODE_HEIGHT + SIBLING_GAP, NODE_WIDTH + LEVEL_GAP]);
    const laidOut = layout(root).descendants();

    nodes = laidOut.map((d) => {
      const hasChildren = d.data.childIds.length > 0;
      const isExpanded = expandedIds.has(d.data.id);
      const marker = hasChildren ? (isExpanded ? '▼' : `▶ +${d.data.childIds.length}`) : '';
      return {
        id: d.data.id,
        type: 'default',
        position: { x: d.y, y: d.x },
        sourcePosition: Position.Right,
        targetPosition: Position.Left,
        data: { label: `${marker ? marker + '  ' : ''}${d.data.name}\n${d.data.actual.toFixed(1)} ${d.data.unit}` },
        style: `width:${NODE_WIDTH}px; white-space: pre-line; font-size: 11px; ${hasChildren ? 'cursor:pointer;' : ''}`,
      };
    });

    edges = laidOut
      .filter((d) => d.parent)
      .map((d) => ({
        id: `${d.parent!.data.id}-${d.data.id}`,
        source: d.parent!.data.id,
        target: d.data.id,
      }));
  });
</script>

<div class="shell py-4">
  <h1 class="mb-2 text-lg font-semibold text-gray-900 dark:text-white">
    VDT Tree — Svelte Flow prototype
  </h1>
  <p class="mb-4 text-sm text-gray-500 dark:text-gray-400">
    Rooted at <code>{rootId}</code>. Click a node with a ▶ marker to expand its children. Spike branch — not wired into nav.
  </p>
</div>

<div style="height: calc(100vh - 10rem);">
  {#if glStore.status === 'ready'}
    <SvelteFlow
      {nodes}
      {edges}
      fitView
      minZoom={0.05}
      maxZoom={2}
      onnodeclick={({ node }) => {
        const n = glStore.tree[node.id];
        if (n && n.childIds.length > 0) toggle(node.id);
      }}
    >
      <Background />
      <Controls />
      <MiniMap />
    </SvelteFlow>
  {:else if glStore.status === 'loading'}
    <p class="shell text-sm text-gray-500">Loading GL tree…</p>
  {:else}
    <p class="shell text-sm text-red-600">Failed to load GL tree ({glStore.status}).</p>
  {/if}
</div>
