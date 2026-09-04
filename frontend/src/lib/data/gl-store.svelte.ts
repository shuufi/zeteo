import type { HierarchyNode } from './types';

export interface GlScopeMeta {
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
let meta = $state<GlScopeMeta | null>(null);

export const glStore = {
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

export async function loadScope(scope: string, periodCode?: string): Promise<void> {
  status = 'loading';
  try {
    const params = new URLSearchParams({ scope });
    if (periodCode) params.set('period', periodCode);
    const res = await fetch(`/api/gl/tree?${params}`);
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
    console.error('Failed to load GL tree', err);
    status = 'error';
  }
}
