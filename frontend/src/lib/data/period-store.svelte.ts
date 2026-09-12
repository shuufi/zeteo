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
 * The same-grain Period one fiscal year before `code` — the client-side half
 * of VDT Variance Analysis's "vs Last Year" pairing (see ADR-0042). Years
 * pair directly; Quarters and Months pair by their fiscal-year-relative order.
 */
export function priorYearSibling(code: string): string | undefined {
  const period = periodStore.tree[code];
  const yearId = periodYearOf(code);
  if (!period || !yearId) return undefined;
  const year = periodStore.tree[yearId];
  const priorYear = Object.values(periodStore.tree).find((p) => p.periodType === 'Year' && p.order === year.order - 1);
  if (!priorYear) return undefined;
  if (period.periodType === 'Year') return priorYear.id;

  function findSameGrainPeriod(parentId: string): string | undefined {
    for (const childId of periodStore.tree[parentId]?.childIds ?? []) {
      const child = periodStore.tree[childId];
      if (!child) continue;
      if (child.periodType === period.periodType && child.order === period.order) return child.id;
      const found = findSameGrainPeriod(childId);
      if (found) return found;
    }
    return undefined;
  }
  return findSameGrainPeriod(priorYear.id);
}

function orderedMonthCodesOfYear(yearId: string): string[] {
  const year = periodStore.tree[yearId];
  if (!year) return [];
  const months: PeriodNode[] = [];
  for (const quarterId of year.childIds) {
    for (const monthId of periodStore.tree[quarterId]?.childIds ?? []) {
      const month = periodStore.tree[monthId];
      if (month) months.push(month);
    }
  }
  months.sort((a, b) => a.order - b.order);
  return months.map((m) => m.id);
}

/**
 * Up to `windowLength` Month codes ending at (and including) `anchorCode`,
 * walking backward across fiscal-year sibling roots — the frontend mirror of
 * backend/periods.py's trailing_month_codes(), used by VDT Trends' Trailing
 * mode (see docs/adr/0042). Returns fewer than `windowLength` codes if
 * history runs out before the window is full (e.g. an anchor near the
 * earliest seeded fiscal year) — a partial window is a deliberate, expected
 * result here, not an error.
 */
export function trailingWindowMonths(anchorCode: string, windowLength = 12): string[] {
  const anchor = periodStore.tree[anchorCode];
  if (!anchor || anchor.periodType !== 'Month') return [];
  const yearId = periodYearOf(anchorCode);
  if (!yearId) return [];

  const years = Object.values(periodStore.tree).filter((p) => p.periodType === 'Year');
  const yearByOrder = new Map(years.map((y) => [y.order, y]));
  const monthsCache = new Map<number, string[]>();
  function monthsOf(yearOrder: number): string[] {
    if (!monthsCache.has(yearOrder)) {
      const year = yearByOrder.get(yearOrder);
      monthsCache.set(yearOrder, year ? orderedMonthCodesOfYear(year.id) : []);
    }
    return monthsCache.get(yearOrder) ?? [];
  }

  const result: string[] = [];
  let yearOrder = periodStore.tree[yearId].order;
  let monthOrder = anchor.order;
  while (result.length < windowLength && yearOrder >= 1) {
    const months = monthsOf(yearOrder);
    if (months.length === 0) break;
    result.push(months[monthOrder - 1]);
    monthOrder -= 1;
    if (monthOrder < 1) {
      yearOrder -= 1;
      monthOrder = 12;
    }
  }
  result.reverse();
  return result;
}

/**
 * A Month period's label reformatted calendar-style, e.g. "Sep FY25" ->
 * "Sep '25" — mirrors backend/periods.py's calendar_month_label(), used by
 * VDT Trends' Trailing mode column headers, where the plain fiscal label
 * would be needlessly verbose and a bare month name would be ambiguous once
 * a window can repeat a month name across two fiscal years (see
 * docs/adr/0042).
 */
export function calendarMonthLabel(code: string): string {
  const label = periodLabel(code);
  const lastSpace = label.lastIndexOf(' ');
  if (lastSpace === -1) return label;
  const monthName = label.slice(0, lastSpace);
  const fiscalYear = label.slice(lastSpace + 1);
  return `${monthName} '${fiscalYear.slice(-2)}`;
}

/**
 * Resolves a Period picker UI id (`"2026"`, `"2026-Q3"`, `"2026-M06"`) into
 * the plain `year`/`quarter`/`month` ints the backend's API actually wants
 * (see docs/adr/0051) — every store that used to forward the id straight
 * through as `?period=` now calls this first. Parses the id's own format
 * rather than looking it up in periodStore.tree: a store's initial fetch
 * (e.g. App.svelte's onMount) can race ahead of loadPeriods() resolving, and
 * this id format is this module's own contract with periods.py's
 * build_period_tree, not something that needs the tree loaded to decode.
 */
export function periodParams(code: string): { year: number; quarter?: number; month?: number } {
  const month = code.match(/^(\d+)-M(\d{2})$/);
  if (month) return { year: Number(month[1]), month: Number(month[2]) };
  const quarter = code.match(/^(\d+)-Q(\d)$/);
  if (quarter) return { year: Number(quarter[1]), quarter: Number(quarter[2]) };
  return { year: Number(code) };
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
