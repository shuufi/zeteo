import type { ComparisonNode } from './types';

export interface ComparisonMeta {
  scope: string;
  scopeKind: 'company' | 'bu';
  partial: boolean;
  sampledCompanyCount: number;
  totalCompanyCount: number;
  node: string;
  periodA: string;
  periodB: string;
}

type Status = 'idle' | 'loading' | 'ready' | 'error' | 'not-yet-modelled';

let tree = $state<Record<string, ComparisonNode>>({});
let status = $state<Status>('idle');
let meta = $state<ComparisonMeta | null>(null);

export const comparisonStore = {
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

export async function loadComparison(scope: string, node: string, periodA: string, periodB: string): Promise<void> {
  status = 'loading';
  try {
    const params = new URLSearchParams({ scope, node, periodA, periodB });
    const res = await fetch(`/api/gl/comparison?${params}`);
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
      partial: data.partial,
      sampledCompanyCount: data.sampledCompanyCount,
      totalCompanyCount: data.totalCompanyCount,
      node: data.node,
      periodA: data.periodA,
      periodB: data.periodB,
    };
    status = 'ready';
  } catch (err) {
    console.error('Failed to load GL comparison', err);
    status = 'error';
  }
}
