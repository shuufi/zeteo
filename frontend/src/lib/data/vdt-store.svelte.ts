import type { HierarchyNode } from './types';

export interface VdtScopeMeta {
  scope: string;
  scopeKind: 'company';
  currency: string;
  partial: boolean;
  sampledCompanyCount: number;
  totalCompanyCount: number;
}

type Status = 'loading' | 'ready' | 'error' | 'not-yet-modelled';

let tree = $state<Record<string, HierarchyNode>>({});
let status = $state<Status>('loading');
let meta = $state<VdtScopeMeta | null>(null);

/**
 * The VDT hierarchy's own tree — a genuinely separate store from glStore
 * (Accounting hierarchy), not a `hierarchy` parameter on the same store,
 * since only VDT Explorer's screens need it and every existing glStore
 * consumer (Trends, DriverDiagnostic) should stay untouched — see
 * docs/adr/0033.
 */
export const vdtStore = {
  get tree() {
    return tree;
  },
  get status() {
    return status;
  },
  get meta() {
    return meta;
  },
};

export async function loadVdtScope(scope: string, periodCode?: string): Promise<void> {
  status = 'loading';
  try {
    const params = new URLSearchParams({ scope });
    if (periodCode) params.set('period', periodCode);
    const res = await fetch(`/api/vdt/tree?${params}`);
    if (!res.ok) throw new Error(`Request failed: ${res.status}`);
    const data = await res.json();
    if (data.notYetModelled) {
      tree = {};
      meta = null;
      status = 'not-yet-modelled';
      return;
    }
    tree = data.nodes;
    meta = {
      scope: data.scope,
      scopeKind: data.scopeKind,
      currency: data.currency,
      partial: data.partial,
      sampledCompanyCount: data.sampledCompanyCount,
      totalCompanyCount: data.totalCompanyCount,
    };
    status = 'ready';
  } catch (err) {
    console.error('Failed to load VDT tree', err);
    status = 'error';
  }
}
