import type { PeriodNode } from './types';

type Status = 'loading' | 'ready' | 'error';

let tree = $state<Record<string, PeriodNode>>({});
let status = $state<Status>('loading');

export const periodStore = {
  get tree() {
    return tree;
  },
  get status() {
    return status;
  },
};

/**
 * A period code's display label — computed on demand from periodStore.tree
 * rather than cached, so it can never go stale (e.g. a deep-link arriving
 * before periods have loaded self-corrects on the next reactive read once
 * they do, instead of freezing on the raw code — see docs/adr/0026).
 */
export function periodLabel(code: string): string {
  return periodStore.tree[code]?.label ?? code;
}

/** Periods are static master data (not scope-dependent) — fetched once, unlike loadScope. */
export async function loadPeriods(): Promise<void> {
  status = 'loading';
  try {
    const res = await fetch('/api/periods');
    if (!res.ok) throw new Error(`Request failed: ${res.status}`);
    tree = await res.json();
    status = 'ready';
  } catch (err) {
    console.error('Failed to load periods', err);
    status = 'error';
  }
}
