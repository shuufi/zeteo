import type { ComparisonNode } from './types';

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
 * VDT Comparison's own comparison tree — a separate store from comparisonStore
 * (Accounting hierarchy, GET /api/gl/comparison) since they hit different
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
    const params = new URLSearchParams({ scope, node, periodA, periodB, ytd: String(ytd) });
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
      periodA: data.periodA,
      periodB: data.periodB,
      ytd: data.ytd,
    };
    status = 'ready';
  } catch (err) {
    console.error('Failed to load VDT comparison', err);
    status = 'error';
  }
}
