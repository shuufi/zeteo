import type { HierarchyNode } from './types';
import { periodParams } from './period-store.svelte';

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
 * The VDT hierarchy's own tree — a genuinely separate store from financialStore
 * (Accounting hierarchy), not a `hierarchy` parameter on the same store,
 * since only VDT Explorer's screens need it and every existing financialStore
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

/**
 * `trailingEnd` (an anchor Month code) is VDT Trends' Trailing mode (see
 * docs/adr/0042) — mutually exclusive with `periodCode` in practice, and
 * wins if both are somehow given, since it's the more specific request.
 */
export async function loadVdtScope(scope: string, periodCode?: string, trailingEnd?: string): Promise<void> {
  status = 'loading';
  try {
    const params = new URLSearchParams({ scope });
    if (trailingEnd) {
      const { year, month } = periodParams(trailingEnd);
      params.set('trailingEndYear', String(year));
      if (month != null) params.set('trailingEndPeriod', String(month));
    } else if (periodCode) {
      const { year, quarter, month } = periodParams(periodCode);
      params.set('year', String(year));
      if (quarter != null) params.set('quarter', String(quarter));
      if (month != null) params.set('month', String(month));
    }
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
