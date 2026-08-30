<script lang="ts">
  import { SvelteFlow, Background, Controls, MiniMap, Position, type Node, type Edge } from '@xyflow/svelte';
  import '@xyflow/svelte/dist/style.css';
  import { stratify, tree as d3tree } from 'd3-hierarchy';
  import { glStore } from '../data/gl-store.svelte';
  import type { VdtNode } from '../data/types';

  const NODE_WIDTH = 220;
  const NODE_HEIGHT = 60;
  const LEVEL_GAP = 100;
  const SIBLING_GAP = 20;

  let { rootId }: { rootId: string } = $props();

  // The root starts expanded. Deeper branches open only when their parent is
  // clicked, keeping large GL hierarchies readable without hiding siblings.
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

  function visibleSubtree(tree: Record<string, VdtNode>, root: string, expanded: Set<string>): VdtNode[] {
    const out: VdtNode[] = [];
    const queue = [root];
    while (queue.length) {
      const id = queue.shift()!;
      const node = tree[id];
      if (!node) continue;
      out.push(node);
      if (expanded.has(id)) queue.push(...node.childIds);
    }
    return out;
  }

  let nodes = $state<Node[]>([]);
  let edges = $state<Edge[]>([]);

  $effect(() => {
    if (glStore.status !== 'ready' || !glStore.tree[rootId]) return;

    const visible = visibleSubtree(glStore.tree, rootId, expandedIds);
    const root = stratify<VdtNode>()
      .id((node) => node.id)
      .parentId((node) => (node.id === rootId ? undefined : (node.parentId ?? undefined)))(visible);
    const layout = d3tree<VdtNode>().nodeSize([NODE_HEIGHT + SIBLING_GAP, NODE_WIDTH + LEVEL_GAP]);
    const laidOut = layout(root).descendants();

    nodes = laidOut.map((item) => {
      const node = item.data;
      const hasChildren = item.data.childIds.length > 0;
      const isExpanded = expandedIds.has(item.data.id);
      const marker = hasChildren ? (isExpanded ? '▼' : `▶ +${item.data.childIds.length}`) : '';

      return {
        id: item.data.id,
        type: 'default',
        position: { x: item.y, y: item.x },
        sourcePosition: Position.Right,
        targetPosition: Position.Left,
        data: { label: `${marker ? marker + '  ' : ''}${node.name}\n${node.actual.toFixed(1)} ${node.unit}` },
        style: `width:${NODE_WIDTH}px; white-space: pre-line; font-size: 11px; ${hasChildren ? 'cursor:pointer;' : ''}`,
      };
    });

    edges = laidOut
      .filter((item) => item.parent)
      .map((item) => ({
        id: `${item.parent!.data.id}-${item.data.id}`,
        source: item.parent!.data.id,
        target: item.data.id,
      }));
  });
</script>

<SvelteFlow
  {nodes}
  {edges}
  fitView
  minZoom={0.05}
  maxZoom={2}
  onnodeclick={({ node }) => {
    const valueDriver = glStore.tree[node.id];
    if (valueDriver?.childIds.length) toggle(node.id);
  }}
>
  <Background />
  <Controls />
  <MiniMap />
</SvelteFlow>
