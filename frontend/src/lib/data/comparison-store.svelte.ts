import type { ComparisonNode } from './types';
import { periodParams } from './period-store.svelte';

export interface ComparisonMeta {
  scope: string;
  scopeKind: 'company';
  currency: string;
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
    const a = periodParams(periodA);
    const b = periodParams(periodB);
    const params = new URLSearchParams({ scope, node, yearA: String(a.year), yearB: String(b.year) });
    if (a.quarter != null) params.set('quarterA', String(a.quarter));
    if (a.month != null) params.set('monthA', String(a.month));
    if (b.quarter != null) params.set('quarterB', String(b.quarter));
    if (b.month != null) params.set('monthB', String(b.month));
    const res = await fetch(`/api/financial/comparison?${params}`);
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
      node: data.node,
      periodA,
      periodB,
    };
    status = 'ready';
  } catch (err) {
    console.error('Failed to load GL comparison', err);
    status = 'error';
  }
}
