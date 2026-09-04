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

/**
 * Walks up to a period's Year ancestor (or returns it unchanged if it already
 * is one) — three fiscal years coexist as sibling roots now (see docs/adr/0032),
 * so "the current year" is no longer just "the only Year in the tree".
 */
export function periodYearOf(code: string): string | undefined {
  let p: PeriodNode | undefined = periodStore.tree[code];
  while (p && p.periodType !== 'Year') {
    p = p.parentId ? periodStore.tree[p.parentId] : undefined;
  }
  return p?.id;
}

/**
 * The Month one fiscal year before `code`'s own fiscal year, same month
 * order — the client-side half of "vs Last Year" (see docs/adr/0034): the
 * user picks one Month, this finds its automatic pairing without a second
 * picker. Mirrors backend/gl_tree.py's _prior_year_code, extended down to
 * Month grain rather than stopping at the Year.
 */
export function priorYearSibling(code: string): string | undefined {
  const month = periodStore.tree[code];
  const yearId = periodYearOf(code);
  if (!month || !yearId) return undefined;
  const year = periodStore.tree[yearId];
  const priorYear = Object.values(periodStore.tree).find((p) => p.periodType === 'Year' && p.order === year.order - 1);
  if (!priorYear) return undefined;

  function findMonth(parentId: string): string | undefined {
    for (const childId of periodStore.tree[parentId]?.childIds ?? []) {
      const child = periodStore.tree[childId];
      if (!child) continue;
      if (child.periodType === 'Month' && child.order === month.order) return child.id;
      const found = findMonth(childId);
      if (found) return found;
    }
    return undefined;
  }
  return findMonth(priorYear.id);
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
