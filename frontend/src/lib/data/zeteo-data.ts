import type {
  VdtNode,
  KpiCard,
  Exception,
  DriverLink,
  LeadingIndicator,
  PlLineItem,
  BridgeStep,
  MonthlySeries,
  Direction,
} from './types';

/**
 * Mock context for the whole prototype: FY26 Q3, vs Budget.
 * Period/comparison chips render this but are inert (see docs/adr/0005).
 * Business is a live picker (see docs/adr/0015) fed by /api/companies, not this mock.
 */
export const context = {
  period: 'FY26 Q3',
  comparison: 'vs Budget',
  refreshedAt: '03:00 today',
};

export const homeKpis: KpiCard[] = [
  { id: 'cfroa', label: 'CFROA', value: '6.2%', delta: '▼ 0.4pp', direction: 'adverse' },
  { id: 'cffo', label: 'CFFO', value: 'RM412m', delta: '▲ 3.1%', direction: 'favourable' },
  { id: 'npat', label: 'NPAT', value: 'RM188m', delta: '▼ 2.0%', direction: 'adverse' },
  { id: 'revenue', label: 'Revenue', value: 'RM1.06bn', delta: '▲ 1.4%', direction: 'favourable' },
  { id: 'expenses', label: 'Expenses', value: 'RM614m', delta: '▲ 5.2% adv', direction: 'adverse', highlighted: true, nodeId: 'expenses' },
  { id: 'net-assets', label: 'Net Assets', value: 'RM3.9bn', delta: '—', direction: 'neutral' },
];

export const attentionException: Exception = {
  title: 'Vessel Operating Cost +8.4% vs Budget',
  impact: 'RM18.2m adverse impact',
  explainedPct: 72,
  targetNodeId: 'vessel-operating-cost',
};

export const topAdverseDrivers: DriverLink[] = [
  { label: 'Crew cost', amount: 'RM9.1m', nodeId: 'crew-cost' },
  { label: 'Repairs & Maint.', amount: 'RM5.4m', nodeId: 'repairs-maintenance' },
  { label: 'Fuel', amount: 'RM3.7m', nodeId: 'fuel' },
];

export const topFavourableDrivers: DriverLink[] = [
  { label: 'Charter rate', amount: '+RM6.2m' },
  { label: 'VOD utilisation', amount: '+RM2.9m' },
];

export const leadingIndicators: LeadingIndicator[] = [
  { label: 'Maintenance backlog', value: '▲ 14 open' },
  { label: 'Off-hire days', value: '▲ 6' },
  { label: 'Crew turnover', value: '3.1%' },
];

/**
 * VDT node tree. Only the Expenses › Vessel Operating Cost › Repairs & Maintenance
 * spine is fully populated (hasFullData). Everything else carries plausible
 * top-line numbers only (hasSummary) so the tree/tables aren't empty, per
 * docs/adr/0004-mock-data-depth.md.
 */
export const vdtNodes: Record<string, VdtNode> = {
  expenses: {
    id: 'expenses',
    name: 'Expenses',
    parentId: null,
    childIds: ['vessel-operating-cost', 'admin-cost', 'corporate-overhead', 'finance-cost', 'other-opex'],
    actual: 614,
    budget: 583.5,
    varPct: 5.2,
    direction: 'adverse',
    unit: 'RM_M',
    hasSummary: true,
    hasFullData: false,
  },
  'vessel-operating-cost': {
    id: 'vessel-operating-cost',
    name: 'Vessel Operating Cost',
    parentId: 'expenses',
    childIds: ['crew-cost', 'repairs-maintenance', 'fuel', 'third-party-services'],
    actual: 231.4,
    budget: 213.2,
    priorYear: 219.8,
    varPct: 8.4,
    varAbs: 18.2,
    direction: 'adverse',
    unit: 'RM_M',
    hasSummary: true,
    hasFullData: false,
    trend: [25, 20, 22, 10, 15, 4],
  },
  'crew-cost': {
    id: 'crew-cost',
    name: 'Crew Cost',
    parentId: 'vessel-operating-cost',
    childIds: [],
    actual: 92.1,
    budget: 83.0,
    varPct: 11,
    direction: 'adverse',
    contributionWidthPct: 70,
    rank: 1,
    unit: 'RM_M',
    hasSummary: true,
    hasFullData: false,
  },
  'repairs-maintenance': {
    id: 'repairs-maintenance',
    name: 'Repairs & Maintenance',
    parentId: 'vessel-operating-cost',
    childIds: [],
    actual: 58.4,
    budget: 53.0,
    priorYear: 49.9,
    varPct: 10.2,
    direction: 'adverse',
    contributionWidthPct: 45,
    rank: 2,
    unit: 'RM_M',
    hasSummary: true,
    hasFullData: true,
    trend: [40, 35, 38, 20, 25, 10, 5, 8],
    drivers: [
      { id: 'dry-dock', label: 'Unplanned dry-dock, Vessel A', varAbs: 2.8, varPct: 52, direction: 'adverse', rank: 1 },
      { id: 'spares-inflation', label: 'Spare parts price inflation', varAbs: 1.4, varPct: 26, direction: 'adverse', rank: 2 },
      { id: 'preventive-deferred', label: 'Preventive maint. deferred', varAbs: 0.7, varPct: 13, direction: 'adverse', rank: 3 },
    ],
    sensitivity: {
      mostSensitive: ['Dry-dock incidence', 'Spares unit price'],
      mostVariable: ['Spares unit price'],
    },
    benchmark: {
      metricLabel: 'Repairs & Maintenance / Vessel Operating Day',
      basis: 'normalised per VOD, same vessel class (LNGC), FY26 YTD',
      bars: [
        { id: 'vessel-a', label: 'Vessel A', valuePerVod: 4120, kind: 'subject' },
        { id: 'fleet-median', label: 'Fleet Median', valuePerVod: 2980, kind: 'internal' },
        { id: 'similar-class', label: 'Similar Class', valuePerVod: 3110, kind: 'internal' },
        { id: 'external', label: 'External Bench.', valuePerVod: 2750, kind: 'external' },
      ],
      rows: [
        { basis: 'MISC Vessel A', valuePerVod: 'RM4,120', gap: '+38%' },
        { basis: 'Fleet median', valuePerVod: 'RM2,980', gap: '—' },
        { basis: 'Similar vessel class', valuePerVod: 'RM3,110', gap: 'baseline' },
        { basis: 'External benchmark (industry, LNGC)', valuePerVod: 'RM2,750', gap: 'data available FY25 only' },
      ],
    },
    reviewSummary: 'Cross-functional review: Finance × Petroleum Ops · 3 validated, 2 under review',
    rootCause: [
      {
        id: 'dry-dock',
        driverLabel: 'Unplanned dry-dock, Vessel A',
        amountLabel: 'RM2.8m, 52%',
        type: 'FACT',
        evidenceOrRationale: 'Evidence: work order #WO-4471, class survey report, invoice batch Q3',
        mitigation: 'Mitigation: schedule remaining dry-docks in off-peak charter windows',
        status: 'Validated',
        analystNotes: 'confirmed with Ops SME, 12 Aug',
      },
      {
        id: 'spares-inflation',
        driverLabel: 'Spare parts price inflation',
        amountLabel: 'RM1.4m, 26%',
        type: 'AI_HYPOTHESIS',
        confidence: 'Medium',
        evidenceOrRationale: 'AI confidence: Medium — rationale: vendor invoice trend +14% QoQ, matched against 2 prior incident reports',
        mitigation: 'Proposed mitigation: renegotiate framework agreement with top-2 suppliers',
        status: 'AI proposed',
      },
      {
        id: 'preventive-deferred',
        driverLabel: 'Preventive maintenance deferred',
        amountLabel: 'RM0.7m, 13%',
        type: 'AI_HYPOTHESIS',
        confidence: 'Low',
        evidenceOrRationale: 'AI confidence: Low — rationale: work-order pattern shift, no confirming SOP match found',
        status: 'Under review',
      },
    ],
  },
  fuel: {
    id: 'fuel',
    name: 'Fuel',
    parentId: 'vessel-operating-cost',
    childIds: [],
    actual: 44.9,
    budget: 41.2,
    varPct: 9,
    direction: 'adverse',
    contributionWidthPct: 30,
    rank: 3,
    unit: 'RM_M',
    hasSummary: true,
    hasFullData: false,
  },
  'third-party-services': {
    id: 'third-party-services',
    name: 'Third-party services',
    parentId: 'vessel-operating-cost',
    childIds: [],
    actual: 36.0,
    budget: 36.0,
    varPct: 0,
    direction: 'neutral',
    rank: 4,
    unit: 'RM_M',
    hasSummary: true,
    hasFullData: false,
  },
  'admin-cost': {
    id: 'admin-cost',
    name: 'Admin Cost',
    parentId: 'expenses',
    childIds: [],
    actual: 42.4,
    budget: 42.0,
    varPct: 1,
    direction: 'adverse',
    unit: 'RM_M',
    hasSummary: true,
    hasFullData: false,
  },
  'corporate-overhead': {
    id: 'corporate-overhead',
    name: 'Corporate Overhead',
    parentId: 'expenses',
    childIds: [],
    actual: 28.6,
    budget: 28.0,
    varPct: 2,
    direction: 'adverse',
    unit: 'RM_M',
    hasSummary: true,
    hasFullData: false,
  },
  'finance-cost': {
    id: 'finance-cost',
    name: 'Finance Cost',
    parentId: 'expenses',
    childIds: [],
    actual: 19.8,
    budget: 20.0,
    priorYear: 18.5,
    varPct: -1,
    direction: 'favourable',
    unit: 'RM_M',
    hasSummary: true,
    hasFullData: false,
  },
  'other-opex': {
    id: 'other-opex',
    name: 'Other Operating Costs',
    parentId: 'expenses',
    childIds: [],
    actual: 12.3,
    budget: 11.9,
    varPct: 3,
    direction: 'adverse',
    unit: 'RM_M',
    hasSummary: true,
    hasFullData: false,
  },

  // Full P&L statement lines (Financial Performance landing, /financial).
  // Vessel Operating Cost and Finance Cost above are reused as-is for their
  // matching statement rows rather than duplicated — see docs/adr/0013.
  'freight-charter-revenue': {
    id: 'freight-charter-revenue',
    name: 'Freight & Charter Revenue',
    parentId: 'gross-profit',
    childIds: [], // populated below by buildMockSplit once its children exist
    actual: 1216.1,
    budget: 1118.0,
    priorYear: 1010.5,
    varPct: pct(1216.1, 1118.0),
    direction: 'favourable',
    unit: 'RM_M',
    hasSummary: true,
    hasFullData: false,
  },
  'voyage-expenses': {
    id: 'voyage-expenses',
    name: 'Voyage Expenses',
    parentId: 'gross-profit',
    childIds: [],
    actual: 489.0,
    budget: 447.7,
    priorYear: 403.0,
    varPct: pct(489.0, 447.7),
    direction: 'adverse',
    unit: 'RM_M',
    hasSummary: true,
    hasFullData: false,
  },
  'depreciation-amortisation': {
    id: 'depreciation-amortisation',
    name: 'Depreciation & Amortisation',
    parentId: 'operating-profit-ebit',
    childIds: [],
    actual: 61.0,
    budget: 58.0,
    priorYear: 55.0,
    varPct: pct(61.0, 58.0),
    direction: 'adverse',
    unit: 'RM_M',
    hasSummary: true,
    hasFullData: false,
  },
  'g-and-a-expenses': {
    id: 'g-and-a-expenses',
    name: 'General & Administrative Expenses',
    parentId: 'operating-profit-ebit',
    childIds: [],
    actual: 15.0,
    budget: 14.0,
    priorYear: 13.0,
    varPct: pct(15.0, 14.0),
    direction: 'adverse',
    unit: 'RM_M',
    hasSummary: true,
    hasFullData: false,
  },
  'other-operating-income': {
    id: 'other-operating-income',
    name: 'Other Operating Income',
    parentId: 'operating-profit-ebit',
    childIds: [],
    actual: 3.0,
    budget: 2.5,
    priorYear: 2.0,
    varPct: pct(3.0, 2.5),
    direction: 'favourable',
    unit: 'RM_M',
    hasSummary: true,
    hasFullData: false,
  },
  'other-operating-expenses': {
    id: 'other-operating-expenses',
    name: 'Other Operating Expenses',
    parentId: 'operating-profit-ebit',
    childIds: [],
    actual: 8.5,
    budget: 6.0,
    priorYear: 6.0,
    varPct: pct(8.5, 6.0),
    direction: 'adverse',
    unit: 'RM_M',
    hasSummary: true,
    hasFullData: false,
  },
  'finance-income': {
    id: 'finance-income',
    name: 'Finance Income',
    parentId: 'profit-before-tax',
    childIds: [],
    actual: 2.0,
    budget: 1.5,
    priorYear: 1.5,
    varPct: pct(2.0, 1.5),
    direction: 'favourable',
    unit: 'RM_M',
    hasSummary: true,
    hasFullData: false,
  },
  'jv-share-profit': {
    id: 'jv-share-profit',
    name: 'Share of Profit — JV / Pool Arrangements',
    parentId: 'profit-before-tax',
    childIds: [],
    actual: 5.0,
    budget: 4.0,
    priorYear: 3.5,
    varPct: pct(5.0, 4.0),
    direction: 'favourable',
    unit: 'RM_M',
    hasSummary: true,
    hasFullData: false,
  },
  'fx-gain-loss': {
    id: 'fx-gain-loss',
    name: 'Foreign Exchange Gain / (Loss)',
    parentId: 'profit-before-tax',
    childIds: [],
    actual: 0.0,
    budget: 0.0,
    priorYear: 0.0,
    varPct: 0,
    direction: 'neutral',
    unit: 'RM_M',
    hasSummary: true,
    hasFullData: false,
  },
  'tax-expense': {
    id: 'tax-expense',
    name: 'Tax Expense',
    parentId: 'npat',
    childIds: [],
    actual: 44.4,
    budget: 40.0,
    priorYear: 34.0,
    varPct: pct(44.4, 40.0),
    direction: 'adverse',
    unit: 'RM_M',
    hasSummary: true,
    hasFullData: false,
  },
};

/**
 * Statement subtotals (Gross Profit, EBIT, Profit Before Tax, NPAT) are not
 * stored magnitudes — they're computed by summing their own contributing
 * lines (see rollUp below), so they can never drift out of sync with the
 * leaf figures above, including the two reused nodes. See docs/adr/0013.
 */
export function pct(actual: number, base: number): number {
  if (base === 0) return 0;
  return Number((((actual - base) / base) * 100).toFixed(1));
}

function subtotalDirection(varPct: number): Direction {
  return varPct >= 0 ? 'favourable' : 'adverse';
}

type RollUpField = 'actual' | 'budget' | 'priorYear';
function rollUp(refs: { id: string; sign: 1 | -1 }[], field: RollUpField): number {
  return Number(
    refs
      .reduce((sum, { id, sign }) => sum + sign * (vdtNodes[id]?.[field] ?? 0), 0)
      .toFixed(1)
  );
}

function buildSubtotal(
  id: string,
  name: string,
  parentId: string | null,
  refs: { id: string; sign: 1 | -1 }[]
): VdtNode {
  const actual = rollUp(refs, 'actual');
  const budget = rollUp(refs, 'budget');
  const priorYear = rollUp(refs, 'priorYear');
  const varPct = pct(actual, budget);
  return {
    id,
    name,
    parentId,
    childIds: refs.map((r) => r.id),
    actual,
    budget,
    priorYear,
    varPct,
    direction: subtotalDirection(varPct),
    unit: 'RM_M',
    hasSummary: true,
    hasFullData: false,
  };
}

const grossProfitRefs: { id: string; sign: 1 | -1 }[] = [
  { id: 'freight-charter-revenue', sign: 1 },
  { id: 'voyage-expenses', sign: -1 },
  { id: 'vessel-operating-cost', sign: -1 },
];
vdtNodes['gross-profit'] = buildSubtotal('gross-profit', 'Gross Profit', 'operating-profit-ebit', grossProfitRefs);

const ebitRefs: { id: string; sign: 1 | -1 }[] = [
  { id: 'gross-profit', sign: 1 },
  { id: 'depreciation-amortisation', sign: -1 },
  { id: 'g-and-a-expenses', sign: -1 },
  { id: 'other-operating-income', sign: 1 },
  { id: 'other-operating-expenses', sign: -1 },
];
vdtNodes['operating-profit-ebit'] = buildSubtotal('operating-profit-ebit', 'Operating Profit / EBIT', 'profit-before-tax', ebitRefs);

const pbtRefs: { id: string; sign: 1 | -1 }[] = [
  { id: 'operating-profit-ebit', sign: 1 },
  { id: 'finance-cost', sign: -1 },
  { id: 'finance-income', sign: 1 },
  { id: 'jv-share-profit', sign: 1 },
  { id: 'fx-gain-loss', sign: 1 },
];
vdtNodes['profit-before-tax'] = buildSubtotal('profit-before-tax', 'Profit Before Tax', 'npat', pbtRefs);

const npatRefs: { id: string; sign: 1 | -1 }[] = [
  { id: 'profit-before-tax', sign: 1 },
  { id: 'tax-expense', sign: -1 },
];
vdtNodes['npat'] = buildSubtotal('npat', 'NPAT', null, npatRefs);

/**
 * VdtRanked only renders a driver table when children carry `rank` (see
 * VdtRanked.svelte) — assign rank/contributionWidthPct here, scoped to each
 * subtotal's own child group, so drilling into a P&L subtotal shows a
 * ranked breakdown instead of falling through to NotYetModelled.
 */
function assignRanks(childIds: string[]): void {
  const items = childIds.map((id) => vdtNodes[id]).filter(Boolean);
  const ranked = [...items].sort(
    (a, b) => Math.abs(b.actual - b.budget) - Math.abs(a.actual - a.budget)
  );
  const maxAbs = Math.max(...ranked.map((n) => Math.abs(n.actual - n.budget)), 1);
  ranked.forEach((n, i) => {
    n.varAbs = Number(Math.abs(n.actual - n.budget).toFixed(1));
    n.rank = i + 1;
    n.contributionWidthPct = Math.round((Math.abs(n.actual - n.budget) / maxAbs) * 100);
  });
}
assignRanks(grossProfitRefs.map((r) => r.id));
assignRanks(ebitRefs.map((r) => r.id));
assignRanks(pbtRefs.map((r) => r.id));
assignRanks(npatRefs.map((r) => r.id));

const costOfRevenueRefs: { id: string; sign: 1 | -1 }[] = [
  { id: 'voyage-expenses', sign: 1 },
  { id: 'vessel-operating-cost', sign: 1 },
];

/**
 * Two synthetic rows built for the Financial Performance statement so it
 * reads as a standard income statement (Revenue → Cost of Revenue → Gross
 * Profit → G&A → PBT → Tax → NPAT) instead of the full EBIT/financing
 * breakdown used elsewhere in the VDT tree. 'ga-combined' nets every line
 * between Gross Profit and PBT (D&A, G&A, other opex/income, financing) into
 * one figure, computed as GP − PBT so the statement always foots exactly.
 */
function costTypeDirection(varPct: number): Direction {
  return varPct >= 0 ? 'adverse' : 'favourable';
}

const costOfRevenueActual = rollUp(costOfRevenueRefs, 'actual');
const costOfRevenueBudget = rollUp(costOfRevenueRefs, 'budget');
const costOfRevenuePriorYear = rollUp(costOfRevenueRefs, 'priorYear');
const costOfRevenueVarPct = pct(costOfRevenueActual, costOfRevenueBudget);
vdtNodes['cost-of-revenue'] = {
  id: 'cost-of-revenue',
  name: 'Cost of Revenue',
  parentId: 'gross-profit',
  childIds: costOfRevenueRefs.map((r) => r.id),
  actual: costOfRevenueActual,
  budget: costOfRevenueBudget,
  priorYear: costOfRevenuePriorYear,
  varPct: costOfRevenueVarPct,
  direction: costTypeDirection(costOfRevenueVarPct),
  unit: 'RM_M',
  hasSummary: true,
  hasFullData: false,
};

const gaCombinedActual = Number((vdtNodes['gross-profit'].actual - vdtNodes['profit-before-tax'].actual).toFixed(1));
const gaCombinedBudget = Number((vdtNodes['gross-profit'].budget - vdtNodes['profit-before-tax'].budget).toFixed(1));
const gaCombinedPriorYear = Number(
  ((vdtNodes['gross-profit'].priorYear ?? 0) - (vdtNodes['profit-before-tax'].priorYear ?? 0)).toFixed(1)
);
const gaCombinedVarPct = pct(gaCombinedActual, gaCombinedBudget);
vdtNodes['ga-combined'] = {
  id: 'ga-combined',
  name: 'General & Administrative Expenses',
  parentId: 'profit-before-tax',
  childIds: [],
  actual: gaCombinedActual,
  budget: gaCombinedBudget,
  priorYear: gaCombinedPriorYear,
  varPct: gaCombinedVarPct,
  direction: costTypeDirection(gaCombinedVarPct),
  unit: 'RM_M',
  hasSummary: true,
  hasFullData: false,
};

/**
 * Splits a parent P&L line into mock sub-lines by revenue/cost share, with
 * the last entry absorbing the rounding remainder so the children always
 * foot exactly back to the parent's actual/budget/priorYear.
 */
function buildMockSplit(
  parentId: string,
  entries: { id: string; name: string; share: number }[],
  direction: Direction
): void {
  const parent = vdtNodes[parentId];
  let remActual = parent.actual;
  let remBudget = parent.budget;
  let remPriorYear = parent.priorYear ?? 0;
  entries.forEach((e, i) => {
    const isLast = i === entries.length - 1;
    const actual = isLast ? Number(remActual.toFixed(1)) : Number((parent.actual * e.share).toFixed(1));
    const budget = isLast ? Number(remBudget.toFixed(1)) : Number((parent.budget * e.share).toFixed(1));
    const priorYear = isLast
      ? Number(remPriorYear.toFixed(1))
      : Number(((parent.priorYear ?? 0) * e.share).toFixed(1));
    remActual = Number((remActual - actual).toFixed(1));
    remBudget = Number((remBudget - budget).toFixed(1));
    remPriorYear = Number((remPriorYear - priorYear).toFixed(1));
    vdtNodes[e.id] = {
      id: e.id,
      name: e.name,
      parentId,
      childIds: [],
      actual,
      budget,
      priorYear,
      varPct: pct(actual, budget),
      direction,
      unit: 'RM_M',
      hasSummary: true,
      hasFullData: false,
    };
  });
  parent.childIds = entries.map((e) => e.id);
}

/** Revenue and Voyage Expenses have no real sub-line data in the mock tree, so their
 * breakdown below is an invented split by share — unlike Vessel Operating Cost, whose
 * children (crew-cost, repairs-maintenance, fuel, third-party-services) are real. */
const revenueSplit = [
  { id: 'time-charter-revenue', name: 'Time Charter Revenue', share: 0.42 },
  { id: 'spot-voyage-revenue', name: 'Spot/Voyage Freight Revenue', share: 0.2 },
  { id: 'offshore-charter-revenue', name: 'Offshore (FPSO/FSO) Charter Revenue', share: 0.18 },
  { id: 'marine-heavy-engineering-revenue', name: 'Marine & Heavy Engineering Revenue', share: 0.1 },
  { id: 'demurrage-income', name: 'Demurrage & Freight Ancillary Income', share: 0.05 },
  { id: 'technical-management-fee-revenue', name: 'Ship/Technical Management Fee Income', share: 0.05 },
];
buildMockSplit('freight-charter-revenue', revenueSplit, 'favourable');

const voyageExpenseSplit = [
  { id: 'bunker-fuel-cost', name: 'Bunker/Fuel Cost', share: 0.62 },
  { id: 'port-canal-dues', name: 'Port & Canal Dues', share: 0.28 },
  { id: 'brokerage-commissions', name: 'Brokerage & Commissions', share: 0.1 },
];
buildMockSplit('voyage-expenses', voyageExpenseSplit, 'adverse');

export const pnlRows: PlLineItem[] = [
  { nodeId: 'freight-charter-revenue', label: 'Revenue', sign: 1, indent: 0, isSubtotal: true },
  { nodeId: 'time-charter-revenue', label: 'Time Charter Revenue', sign: 1, indent: 1, isSubtotal: true, group: 'freight-charter-revenue' },
  {
    nodeId: 'time-charter-rate',
    label: 'Avg. Daily Charter Rate',
    sign: 1,
    indent: 1,
    group: 'time-charter-revenue',
    kind: 'operational',
    unit: 'usd-per-day',
  },
  {
    nodeId: 'time-charter-utilization',
    label: 'Utilization / On-hire Rate',
    sign: 1,
    indent: 1,
    group: 'time-charter-revenue',
    kind: 'operational',
    unit: 'percent',
  },
  {
    nodeId: 'time-charter-offhire-days',
    label: 'Off-hire Days (fleet)',
    sign: 1,
    indent: 1,
    group: 'time-charter-revenue',
    kind: 'operational',
    unit: 'days',
  },
  { nodeId: 'spot-voyage-revenue', label: 'Spot/Voyage Revenue', sign: 1, indent: 1, isSubtotal: true, group: 'freight-charter-revenue' },
  {
    nodeId: 'spot-voyage-rate',
    label: 'Avg. Spot/Voyage TCE Rate',
    sign: 1,
    indent: 1,
    group: 'spot-voyage-revenue',
    kind: 'operational',
    unit: 'usd-per-day',
  },
  {
    nodeId: 'spot-voyage-days',
    label: 'Spot Voyage Days (fleet)',
    sign: 1,
    indent: 1,
    group: 'spot-voyage-revenue',
    kind: 'operational',
    unit: 'days',
  },
  { nodeId: 'offshore-charter-revenue', label: 'FPSO/FSO Charter Revenue', sign: 1, indent: 1, isSubtotal: true, group: 'freight-charter-revenue' },
  {
    nodeId: 'offshore-charter-rate',
    label: 'Avg. Daily Charter Rate',
    sign: 1,
    indent: 1,
    group: 'offshore-charter-revenue',
    kind: 'operational',
    unit: 'usd-per-day',
  },
  {
    nodeId: 'offshore-uptime',
    label: 'Fleet Uptime / Availability',
    sign: 1,
    indent: 1,
    group: 'offshore-charter-revenue',
    kind: 'operational',
    unit: 'percent',
  },
  { nodeId: 'marine-heavy-engineering-revenue', label: 'Marine & Heavy Eng. Revenue', sign: 1, indent: 1, isSubtotal: true, group: 'freight-charter-revenue' },
  {
    nodeId: 'marine-engineering-completion-rate',
    label: 'Avg. Project Completion Rate',
    sign: 1,
    indent: 1,
    group: 'marine-heavy-engineering-revenue',
    kind: 'operational',
    unit: 'percent',
  },
  {
    nodeId: 'marine-engineering-active-projects',
    label: 'Active Projects',
    sign: 1,
    indent: 1,
    group: 'marine-heavy-engineering-revenue',
    kind: 'operational',
    unit: 'count',
  },
  { nodeId: 'demurrage-income', label: 'Demurrage & Ancillary Income', sign: 1, indent: 1, isSubtotal: true, group: 'freight-charter-revenue' },
  {
    nodeId: 'demurrage-days',
    label: 'Demurrage Days Billed',
    sign: 1,
    indent: 1,
    group: 'demurrage-income',
    kind: 'operational',
    unit: 'days',
  },
  {
    nodeId: 'demurrage-rate',
    label: 'Avg. Demurrage Rate',
    sign: 1,
    indent: 1,
    group: 'demurrage-income',
    kind: 'operational',
    unit: 'usd-per-day',
  },
  { nodeId: 'technical-management-fee-revenue', label: 'Technical Mgmt Fee Income', sign: 1, indent: 1, isSubtotal: true, group: 'freight-charter-revenue' },
  {
    nodeId: 'technical-management-vessels',
    label: 'Vessels Under Management',
    sign: 1,
    indent: 1,
    group: 'technical-management-fee-revenue',
    kind: 'operational',
    unit: 'count',
  },
  {
    nodeId: 'technical-management-fee-per-vessel',
    label: 'Avg. Fee per Vessel',
    sign: 1,
    indent: 1,
    group: 'technical-management-fee-revenue',
    kind: 'operational',
    unit: 'usd-per-month',
  },
  { nodeId: 'cost-of-revenue', label: 'Cost of Revenue', sign: -1, indent: 0, isSubtotal: true },
  { nodeId: 'voyage-expenses', label: 'Voyage Expenses', sign: -1, indent: 1, isSubtotal: true, group: 'cost-of-revenue' },
  { nodeId: 'bunker-fuel-cost', label: 'Bunker/Fuel Cost', sign: -1, indent: 1, group: 'voyage-expenses' },
  { nodeId: 'port-canal-dues', label: 'Port & Canal Dues', sign: -1, indent: 1, group: 'voyage-expenses' },
  { nodeId: 'brokerage-commissions', label: 'Brokerage & Commissions', sign: -1, indent: 1, group: 'voyage-expenses' },
  { nodeId: 'vessel-operating-cost', label: 'Vessel Operating Costs', sign: -1, indent: 1, isSubtotal: true, group: 'cost-of-revenue' },
  { nodeId: 'crew-cost', label: 'Crew Cost', sign: -1, indent: 1, group: 'vessel-operating-cost' },
  { nodeId: 'repairs-maintenance', label: 'Repairs & Maintenance', sign: -1, indent: 1, group: 'vessel-operating-cost' },
  { nodeId: 'fuel', label: 'Vessel Fuel & Lubricants', sign: -1, indent: 1, group: 'vessel-operating-cost' },
  { nodeId: 'third-party-services', label: 'Third-party Services', sign: -1, indent: 1, group: 'vessel-operating-cost' },
  { nodeId: 'gross-profit', label: 'Gross Profit', sign: 1, indent: 0, isSubtotal: true },
  { nodeId: 'ga-combined', label: 'General & Administrative Expenses', sign: -1, indent: 0 },
  { nodeId: 'profit-before-tax', label: 'Profit Before Tax', sign: 1, indent: 0, isSubtotal: true },
  { nodeId: 'tax-expense', label: 'Tax Expense', sign: -1, indent: 1 },
  { nodeId: 'npat', label: 'NPAT', sign: 1, indent: 0, isSubtotal: true, isFinal: true },
];

export function formatRmAuto(value: number): string {
  if (Math.abs(value) >= 1000) return `RM${(value / 1000).toFixed(2)}bn`;
  return formatRm(value);
}

/**
 * Monthly (non-cumulative) actuals, January–December, backing the Financial
 * Performance trend chart. Financial Performance shows performance over the
 * year rather than budget/prior-year comparisons — see docs/adr/0013.
 */
export const months: string[] = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

const monthlyRevenue = [118, 121, 125, 129, 133, 137, 141, 145, 148, 151, 154, 158];
const monthlyCostOfRevenue = [70, 72, 74, 77, 80, 82, 85, 88, 90, 93, 95, 98];
const monthlyOpex = [7.5, 7.6, 7.8, 7.9, 8.1, 8.3, 8.5, 8.7, 8.9, 9.1, 9.3, 9.6];
const monthlyNpat = [28, 29, 31, 33, 35, 37, 39, 41, 43, 45, 47, 50];

/** Normalised month-of-year weighting (sums to 1) for lines with no explicit monthly curve. */
const MONTHLY_GROWTH_CURVE = [0.07, 0.072, 0.075, 0.078, 0.08, 0.083, 0.085, 0.088, 0.09, 0.092, 0.093, 0.094];
function spreadByCurve(total: number): number[] {
  return MONTHLY_GROWTH_CURVE.map((w) => Number((w * total).toFixed(1)));
}

/**
 * Monthly split of P&L line items, derived from the aggregate monthly
 * curves above so each line reconciles to its own actual and the
 * Revenue/Cost of Revenue/OPEX chart stays consistent with the table below.
 */
const voyageExpenseShare =
  vdtNodes['voyage-expenses'].actual / (vdtNodes['voyage-expenses'].actual + vdtNodes['vessel-operating-cost'].actual);
const monthlyVoyageExpenses = monthlyCostOfRevenue.map((v) => Number((v * voyageExpenseShare).toFixed(1)));
const monthlyVesselOperatingCost = monthlyCostOfRevenue.map((v, i) => Number((v - monthlyVoyageExpenses[i]).toFixed(1)));

const monthlyOtherOperatingIncome = spreadByCurve(vdtNodes['other-operating-income'].actual);
const grossOpexMonthly = monthlyOpex.map((v, i) => v + monthlyOtherOperatingIncome[i]);
const opexExpenseBase =
  vdtNodes['depreciation-amortisation'].actual + vdtNodes['g-and-a-expenses'].actual + vdtNodes['other-operating-expenses'].actual;
const monthlyDepreciationAmortisation = grossOpexMonthly.map((v) =>
  Number(((v * vdtNodes['depreciation-amortisation'].actual) / opexExpenseBase).toFixed(1))
);
const monthlyGAndAExpenses = grossOpexMonthly.map((v) =>
  Number(((v * vdtNodes['g-and-a-expenses'].actual) / opexExpenseBase).toFixed(1))
);
const monthlyOtherOperatingExpenses = grossOpexMonthly.map((v, i) =>
  Number((v - monthlyDepreciationAmortisation[i] - monthlyGAndAExpenses[i]).toFixed(1))
);

const monthlyFinanceCost = spreadByCurve(vdtNodes['finance-cost'].actual);
const monthlyFinanceIncome = spreadByCurve(vdtNodes['finance-income'].actual);
const monthlyJvShareProfit = spreadByCurve(vdtNodes['jv-share-profit'].actual);
const monthlyFxGainLoss = spreadByCurve(vdtNodes['fx-gain-loss'].actual);
const monthlyTaxExpense = spreadByCurve(vdtNodes['tax-expense'].actual);

function monthlySubtotal(refs: { id: string; sign: 1 | -1 }[]): number[] {
  return months.map((_, i) =>
    Number(refs.reduce((sum, { id, sign }) => sum + sign * (monthlyPnl[id]?.[i] ?? 0), 0).toFixed(1))
  );
}

/** Monthly (Jan–Dec) actuals per P&L row, keyed by nodeId — powers the monthly columns in the Full P&L table. */
export const monthlyPnl: Record<string, number[]> = {
  'freight-charter-revenue': monthlyRevenue,
  'cost-of-revenue': monthlyCostOfRevenue,
  'voyage-expenses': monthlyVoyageExpenses,
  'vessel-operating-cost': monthlyVesselOperatingCost,
  'depreciation-amortisation': monthlyDepreciationAmortisation,
  'g-and-a-expenses': monthlyGAndAExpenses,
  'other-operating-income': monthlyOtherOperatingIncome,
  'other-operating-expenses': monthlyOtherOperatingExpenses,
  'finance-cost': monthlyFinanceCost,
  'finance-income': monthlyFinanceIncome,
  'jv-share-profit': monthlyJvShareProfit,
  'fx-gain-loss': monthlyFxGainLoss,
  'tax-expense': monthlyTaxExpense,
};
monthlyPnl['gross-profit'] = monthlySubtotal(grossProfitRefs);
monthlyPnl['operating-profit-ebit'] = monthlySubtotal(ebitRefs);
monthlyPnl['profit-before-tax'] = monthlySubtotal(pbtRefs);
monthlyPnl['npat'] = monthlySubtotal(npatRefs);
monthlyPnl['ga-combined'] = months.map((_, i) =>
  Number((monthlyPnl['gross-profit'][i] - monthlyPnl['profit-before-tax'][i]).toFixed(1))
);

/**
 * Splits a parent's monthly series across sub-line items by share, month by
 * month, with the last entry absorbing that month's rounding remainder so
 * the children always sum back to the parent's monthly figure exactly.
 */
function splitMonthly(entries: { id: string; share: number }[], parentMonthly: number[]): void {
  const series: number[][] = entries.map(() => []);
  parentMonthly.forEach((total) => {
    let remaining = total;
    entries.forEach((e, i) => {
      const isLast = i === entries.length - 1;
      const value = isLast ? Number(remaining.toFixed(1)) : Number((total * e.share).toFixed(1));
      remaining = Number((remaining - value).toFixed(1));
      series[i].push(value);
    });
  });
  entries.forEach((e, i) => {
    monthlyPnl[e.id] = series[i];
  });
}

splitMonthly(revenueSplit, monthlyRevenue);
splitMonthly(voyageExpenseSplit, monthlyVoyageExpenses);

/** Vessel Operating Cost's children are real (not invented) — split its monthly
 * series using their actual real-value shares, rather than hand-picked shares. */
const vesselOperatingCostSplit = ['crew-cost', 'repairs-maintenance', 'fuel', 'third-party-services'].map((id) => ({
  id,
  share: vdtNodes[id].actual / vdtNodes['vessel-operating-cost'].actual,
}));
splitMonthly(vesselOperatingCostSplit, monthlyVesselOperatingCost);

/**
 * Operational value drivers behind Time Charter Revenue (rate, utilization,
 * off-hire days) — not GL amounts, so they live outside the RM_M rollup
 * tree entirely. Illustrative trend only; not reconciled to the revenue
 * figure above (that would require a real fleet-days model).
 */
monthlyPnl['time-charter-rate'] = [42, 43, 44, 45.5, 47, 48.5, 50, 51.5, 52.5, 53.5, 54.5, 56];
monthlyPnl['time-charter-utilization'] = [96.2, 96.5, 96.8, 97.0, 97.2, 97.5, 97.6, 97.8, 98.0, 98.1, 98.3, 98.5];
monthlyPnl['time-charter-offhire-days'] = [9, 8.5, 8, 7.5, 7, 6.5, 6, 5.5, 5, 4.5, 4, 3.5];

/** Same treatment for the rest of the Revenue lines — illustrative operational drivers only. */
monthlyPnl['spot-voyage-rate'] = [30, 31, 33, 35, 36, 38, 40, 41, 42, 44, 45, 47];
monthlyPnl['spot-voyage-days'] = [180, 182, 185, 188, 190, 193, 195, 197, 199, 201, 203, 205];

monthlyPnl['offshore-charter-rate'] = [220, 222, 224, 226, 228, 230, 232, 234, 236, 238, 240, 242];
monthlyPnl['offshore-uptime'] = [97.0, 97.2, 97.5, 97.6, 97.8, 98.0, 98.1, 98.2, 98.4, 98.5, 98.6, 98.8];

monthlyPnl['marine-engineering-completion-rate'] = [40, 45, 50, 55, 58, 62, 66, 70, 74, 78, 82, 86];
monthlyPnl['marine-engineering-active-projects'] = [5, 5, 6, 6, 6, 7, 7, 7, 7, 8, 8, 8];

monthlyPnl['demurrage-days'] = [12, 11, 13, 10, 9, 11, 10, 9, 8, 9, 8, 7];
monthlyPnl['demurrage-rate'] = [18, 18, 19, 19, 20, 20, 21, 21, 22, 22, 23, 23];

monthlyPnl['technical-management-vessels'] = [22, 22, 23, 23, 23, 24, 24, 24, 25, 25, 25, 26];
monthlyPnl['technical-management-fee-per-vessel'] = [45, 45, 46, 46, 47, 47, 48, 48, 49, 49, 50, 50];

export function cumulative(values: number[]): number[] {
  let running = 0;
  return values.map((v) => {
    running += v;
    return Number(running.toFixed(1));
  });
}

export const financialKpis: KpiCard[] = [
  {
    id: 'revenue-ytd',
    label: 'Revenue YTD',
    value: formatRmAuto(vdtNodes['freight-charter-revenue'].actual),
    trend: cumulative(monthlyRevenue),
  },
  {
    id: 'cost-of-revenue-ytd',
    label: 'Cost of Revenue YTD',
    value: formatRmAuto(rollUp([{ id: 'voyage-expenses', sign: 1 }, { id: 'vessel-operating-cost', sign: 1 }], 'actual')),
    trend: cumulative(monthlyCostOfRevenue),
  },
  {
    id: 'gross-profit-ytd',
    label: 'Gross Profit YTD',
    value: formatRmAuto(vdtNodes['gross-profit'].actual),
    trend: cumulative(monthlyRevenue.map((r, i) => r - monthlyCostOfRevenue[i])),
  },
  {
    id: 'npat-ytd',
    label: 'NPAT YTD',
    value: formatRmAuto(vdtNodes['npat'].actual),
    trend: cumulative(monthlyNpat),
  },
];

export const monthlyPerformanceChart: MonthlySeries[] = [
  { label: 'Revenue', values: monthlyRevenue, colorClass: 'stroke-gray-900 dark:stroke-gray-50' },
  { label: 'Cost of Revenue', values: monthlyCostOfRevenue, colorClass: 'stroke-red-600 dark:stroke-red-400' },
  { label: 'OPEX', values: monthlyOpex, colorClass: 'stroke-indigo-600 dark:stroke-indigo-400' },
];

export const profitBridgeSteps: BridgeStep[] = [
  { label: 'Revenue', value: vdtNodes['freight-charter-revenue'].actual, kind: 'total' },
  {
    label: 'Cost of Revenue',
    value: -rollUp([{ id: 'voyage-expenses', sign: 1 }, { id: 'vessel-operating-cost', sign: 1 }], 'actual'),
    kind: 'decrease',
  },
  { label: 'Gross Profit', value: vdtNodes['gross-profit'].actual, kind: 'total' },
  {
    label: 'OPEX',
    value: -rollUp(
      [
        { id: 'depreciation-amortisation', sign: 1 },
        { id: 'g-and-a-expenses', sign: 1 },
        { id: 'other-operating-expenses', sign: 1 },
        { id: 'other-operating-income', sign: -1 },
      ],
      'actual'
    ),
    kind: 'decrease',
  },
  { label: 'Operating Profit', value: vdtNodes['operating-profit-ebit'].actual, kind: 'total' },
  {
    label: 'Finance Costs',
    value: -rollUp(
      [
        { id: 'finance-cost', sign: 1 },
        { id: 'finance-income', sign: -1 },
        { id: 'jv-share-profit', sign: -1 },
        { id: 'fx-gain-loss', sign: -1 },
      ],
      'actual'
    ),
    kind: 'decrease',
  },
  { label: 'Profit Before Tax', value: vdtNodes['profit-before-tax'].actual, kind: 'total' },
  { label: 'Tax', value: -vdtNodes['tax-expense'].actual, kind: 'decrease' },
  { label: 'NPAT', value: vdtNodes['npat'].actual, kind: 'total' },
];

export function getNode(id: string): VdtNode | undefined {
  return vdtNodes[id];
}

export function getMonthlyPnl(nodeId: string): number[] | undefined {
  return monthlyPnl[nodeId];
}

export function getChildren(node: VdtNode): VdtNode[] {
  return node.childIds.map((id) => vdtNodes[id]).filter(Boolean) as VdtNode[];
}

export function getAncestors(id: string): VdtNode[] {
  const chain: VdtNode[] = [];
  let current = vdtNodes[id];
  while (current?.parentId) {
    const parent = vdtNodes[current.parentId];
    if (!parent) break;
    chain.unshift(parent);
    current = parent;
  }
  return chain;
}

/**
 * Re-scopes a node's actual/budget/priorYear to a single month, driven by the
 * VDT Explorer's per-cell drill-in from the Financial Performance table.
 * Budget/priorYear have no monthly curve of their own, so they're prorated by
 * the month's share of the node's annual actual — direction is left as-is
 * since inverting it correctly needs revenue-vs-cost context this data
 * doesn't carry per node.
 */
export function getMonthlyNodeView(nodeId: string, monthIndex: number): VdtNode | undefined {
  const node = vdtNodes[nodeId];
  const monthly = monthlyPnl[nodeId];
  if (!node) return undefined;
  const actual = monthly?.[monthIndex];
  if (actual === undefined) return node;
  const share = node.actual !== 0 ? actual / node.actual : 0;
  const budget = Number((node.budget * share).toFixed(1));
  const priorYear = node.priorYear !== undefined ? Number((node.priorYear * share).toFixed(1)) : undefined;
  return {
    ...node,
    actual,
    budget,
    priorYear,
    varPct: pct(actual, budget),
    trend: monthly,
  };
}

/** Children ranked by variance magnitude for a specific month, mirroring assignRanks but computed live. */
export function getMonthlyChildren(node: VdtNode, monthIndex: number): VdtNode[] {
  const kids = getChildren(node).map((child) => getMonthlyNodeView(child.id, monthIndex) ?? child);
  const ranked = [...kids].sort((a, b) => Math.abs(b.actual - b.budget) - Math.abs(a.actual - a.budget));
  const maxAbs = Math.max(...ranked.map((n) => Math.abs(n.actual - n.budget)), 1);
  return ranked.map((n, i) => ({
    ...n,
    varAbs: Number(Math.abs(n.actual - n.budget).toFixed(1)),
    rank: i + 1,
    contributionWidthPct: Math.round((Math.abs(n.actual - n.budget) / maxAbs) * 100),
  }));
}

export function formatVar(varPct: number): string {
  const sign = varPct > 0 ? '+' : varPct < 0 ? '' : '±';
  return `${sign}${varPct}%`;
}

export function formatRm(value: number): string {
  return `RM${value.toFixed(1)}m`;
}
