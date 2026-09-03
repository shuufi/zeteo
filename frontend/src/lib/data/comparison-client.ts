import type { ComparisonNode, DisplayRow } from './types';

export function getComparisonNode(tree: Record<string, ComparisonNode>, id: string): ComparisonNode | undefined {
  return tree[id];
}

export function getComparisonChildren(tree: Record<string, ComparisonNode>, node: ComparisonNode): ComparisonNode[] {
  return node.childIds.map((id) => tree[id]).filter((n): n is ComparisonNode => n !== undefined);
}

/**
 * Flattens a Comparison subtree (see GET /api/gl/comparison, docs/adr/0031)
 * into statement rows — same walk shape as gl-client.ts's buildDisplayRows,
 * reused here since a ComparisonNode carries the same identity/hierarchy
 * fields as a VdtNode, just two periods' values instead of one.
 */
export function buildComparisonRows(tree: Record<string, ComparisonNode>, rootId: string): DisplayRow[] {
  const rows: DisplayRow[] = [];

  function walk(code: string, indent: number): void {
    const node = tree[code];
    if (!node) return;
    const isRoot = node.parentId === null;
    const isDriverGraph = node.nodeType === 'Driver Formula' || node.nodeType === 'Driver';
    const children = getComparisonChildren(tree, node);

    if (!isRoot) {
      rows.push({
        nodeId: code,
        label: node.name,
        indent,
        isSubtotal: children.length > 0 && !isDriverGraph,
        group: node.parentId ?? undefined,
        kind: isDriverGraph ? 'operational' : undefined,
        driverNodeType: node.nodeType === 'Driver Formula' ? 'formula' : node.nodeType === 'Driver' ? 'driver' : undefined,
        unit: isDriverGraph ? (node.unit as DisplayRow['unit']) : undefined,
        expression: node.nodeType === 'Driver Formula' ? node.expression : undefined,
      });
    }

    for (const child of children) {
      walk(child.id, indent + 1);
    }

    if (isRoot) {
      rows.push({ nodeId: code, label: node.name, indent: 0, isSubtotal: true, isFinal: true });
    }
  }

  walk(rootId, 0);
  return rows;
}
