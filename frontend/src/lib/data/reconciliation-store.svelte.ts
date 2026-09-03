import type { HierarchyNode } from './types';

export interface ReconciliationMeta {
  scope: string;
  scopeKind: 'company' | 'bu';
  partial: boolean;
  sampledCompanyCount: number;
  totalCompanyCount: number;
  node: string;
  period: string | null;
}

type Status = 'idle' | 'loading' | 'ready' | 'error' | 'not-yet-modelled';

let accountingTree = $state<Record<string, HierarchyNode>>({});
let vdtTree = $state<Record<string, HierarchyNode>>({});
let status = $state<Status>('idle');
let meta = $state<ReconciliationMeta | null>(null);

/**
 * The Accounting-vs-VDT reconciliation view (GET /api/vdt/reconciliation) —
 * see docs/adr/0033. Two independent subtrees for the same node/scope/period,
 * not one diffed tree like comparison-store — there's no delta here, just
 * each hierarchy's own breakdown, since the two aren't required to reconcile.
 */
export const reconciliationStore = {
  get accountingTree() {
    return accountingTree;
  },
  get vdtTree() {
    return vdtTree;
  },
  get status() {
    return status;
  },
  get meta() {
    return meta;
  },
};

export async function loadReconciliation(scope: string, node: string, periodCode?: string): Promise<void> {
  status = 'loading';
  try {
    const params = new URLSearchParams({ scope, node });
    if (periodCode) params.set('period', periodCode);
    const res = await fetch(`/api/vdt/reconciliation?${params}`);
    if (!res.ok) throw new Error(`Request failed: ${res.status}`);
    const data = await res.json();
    if (data.notYetModelled) {
      accountingTree = {};
      vdtTree = {};
      meta = null;
      status = 'not-yet-modelled';
      return;
    }
    accountingTree = data.accounting.nodes;
    vdtTree = data.vdt.nodes;
    meta = {
      scope: data.scope,
      scopeKind: data.scopeKind,
      partial: data.partial,
      sampledCompanyCount: data.sampledCompanyCount,
      totalCompanyCount: data.totalCompanyCount,
      node: data.node,
      period: data.period,
    };
    status = 'ready';
  } catch (err) {
    console.error('Failed to load VDT reconciliation', err);
    status = 'error';
  }
}
