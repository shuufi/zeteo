import type { DisplayRow, RankedNode, VdtNode } from './types';

export function getNode(tree: Record<string, VdtNode>, id: string): VdtNode | undefined {
  return tree[id];
}

export function getChildren(tree: Record<string, VdtNode>, node: VdtNode): VdtNode[] {
  return node.childIds.map((id) => tree[id]).filter((n): n is VdtNode => n !== undefined);
}

export function getAncestors(tree: Record<string, VdtNode>, id: string): VdtNode[] {
  const chain: VdtNode[] = [];
  let current = tree[id];
  while (current?.parentId) {
    const parent = tree[current.parentId];
    if (!parent) break;
    chain.unshift(parent);
    current = parent;
  }
  return chain;
}

/**
 * Re-scopes a node's actual/budget/priorYear to a single month. Budget/
 * priorYear have no monthly curve of their own, so they're prorated by the
 * month's share of the node's annual actual (see docs/adr/0022, and the old
 * zeteo-data.ts getMonthlyNodeView this replaces).
 */
export function getMonthlyNodeView(tree: Record<string, VdtNode>, nodeId: string, monthIndex: number): VdtNode | undefined {
  const node = tree[nodeId];
  if (!node) return undefined;
  const actual = node.monthlyActual[monthIndex];
  if (actual === undefined) return node;
  const share = node.actual !== 0 ? actual / node.actual : 0;
  return {
    ...node,
    actual,
    budget: Number((node.budget * share).toFixed(3)),
    priorYear: Number((node.priorYear * share).toFixed(3)),
  };
}

/**
 * Children ranked by |actual - budget| variance — the real GL/FSI tree has no
 * curated per-node rank, so every node's children rank live off this one
 * generic walk instead of the old mock's hand-picked ref lists. Operational
 * Driver children are excluded: their units (rate/%/days) aren't comparable
 * to a financial variance in RM_M.
 */
export function rankChildren(tree: Record<string, VdtNode>, node: VdtNode, monthIndex: number | null = null): RankedNode[] {
  const children = getChildren(tree, node).filter((c) => c.nodeType !== 'Operational Driver');
  const scoped = monthIndex === null ? children : children.map((c) => getMonthlyNodeView(tree, c.id, monthIndex) ?? c);
  const ranked = [...scoped].sort((a, b) => Math.abs(b.actual - b.budget) - Math.abs(a.actual - a.budget));
  const maxAbs = Math.max(...ranked.map((n) => Math.abs(n.actual - n.budget)), 1);
  return ranked.map((n, i) => ({
    ...n,
    varAbs: Number(Math.abs(n.actual - n.budget).toFixed(1)),
    rank: i + 1,
    contributionWidthPct: Math.round((Math.abs(n.actual - n.budget) / maxAbs) * 100),
  }));
}

const INDENT_CLASSES = ['pl-0', 'pl-4', 'pl-8', 'pl-12', 'pl-16', 'pl-20'];

export function indentClass(indent: number): string {
  return INDENT_CLASSES[Math.min(indent, INDENT_CLASSES.length - 1)];
}

// Revenue's direct children (PNL-0002) already sit under a "Revenue" row in
// the statement, so repeating the word in their own label is redundant noise.
const REVENUE_NODE_ID = 'PNL-0002';

function stripRedundantRevenueWord(name: string): string {
  return name
    .replace(/\bRevenue\b/g, '')
    .replace(/\s*-\s*-\s*/g, ' - ')
    .replace(/^[\s-]+|[\s-]+$/g, '')
    .replace(/\s{2,}/g, ' ');
}

/**
 * Flattens the GL/FSI tree into Financial Performance's statement rows.
 * Posting GL Account leaves (1083 of them) are never shown individually —
 * only Reporting Root/Node subtotals and attached Operational Driver rows,
 * matching the old mock's curated summary-only P&L (see docs/adr/0022).
 */
export function buildDisplayRows(tree: Record<string, VdtNode>, rootId = 'NPAT'): DisplayRow[] {
  const rows: DisplayRow[] = [];

  function walk(code: string, indent: number): void {
    const node = tree[code];
    if (!node) return;
    const isRoot = node.parentId === null;
    const children = getChildren(tree, node);
    const financialChildren = children.filter((c) => c.nodeType === 'Reporting Node' || c.nodeType === 'Reporting Root');
    const operationalChildren = children.filter((c) => c.nodeType === 'Operational Driver');

    if (!isRoot) {
      rows.push({
        nodeId: code,
        label: node.parentId === REVENUE_NODE_ID ? stripRedundantRevenueWord(node.name) : node.name,
        indent,
        isSubtotal: financialChildren.length > 0 || operationalChildren.length > 0,
        group: node.parentId ?? undefined,
      });
    }

    for (const opChild of operationalChildren) {
      rows.push({
        nodeId: opChild.id,
        label: opChild.name,
        indent: indent + 1,
        kind: 'operational',
        unit: opChild.unit as DisplayRow['unit'],
        group: code,
      });
    }

    for (const child of financialChildren) {
      walk(child.id, indent + 1);
    }

    if (isRoot) {
      rows.push({ nodeId: code, label: node.name, indent: 0, isSubtotal: true, isFinal: true });
    }
  }

  walk(rootId, 0);
  return rows;
}
