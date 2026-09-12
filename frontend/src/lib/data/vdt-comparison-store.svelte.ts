import type { ComparisonNode } from './types';
import { periodParams } from './period-store.svelte';

export interface VdtComparisonMeta {
  scope: string;
  scopeKind: 'company';
  currency: string;
  partial: boolean;
  sampledCompanyCount: number;
  totalCompanyCount: number;
  node: string;
  periodA: string;
  periodB: string;
  ytd: boolean;
}

type Status = 'idle' | 'loading' | 'ready' | 'error' | 'not-yet-modelled';

let tree = $state<Record<string, ComparisonNode>>({});
let status = $state<Status>('idle');
let meta = $state<VdtComparisonMeta | null>(null);

/**
 * VDT Variance Analysis's own comparison tree — a separate store from comparisonStore
 * (Accounting hierarchy, GET /api/financial/comparison) since they hit different
 * endpoints/trees, even though both share the ComparisonNode shape — see
 * docs/adr/0034.
 */
export const vdtComparisonStore = {
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

export async function loadVdtComparison(
  scope: string,
  node: string,
  periodA: string,
  periodB: string,
  ytd: boolean,
): Promise<void> {
  status = 'loading';
  try {
    const a = periodParams(periodA);
    const b = periodParams(periodB);
    const params = new URLSearchParams({ scope, node, yearA: String(a.year), yearB: String(b.year), ytd: String(ytd) });
    if (a.quarter != null) params.set('quarterA', String(a.quarter));
    if (a.month != null) params.set('monthA', String(a.month));
    if (b.quarter != null) params.set('quarterB', String(b.quarter));
    if (b.month != null) params.set('monthB', String(b.month));
    const res = await fetch(`/api/vdt/comparison?${params}`);
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
      ytd: data.ytd,
    };
    status = 'ready';
  } catch (err) {
    console.error('Failed to load VDT comparison', err);
    status = 'error';
  }
}
