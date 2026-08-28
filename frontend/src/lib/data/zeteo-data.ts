import type {
  VdtNode,
  KpiCard,
  Exception,
  DriverLink,
  LeadingIndicator,
  PlLineItem,
  BridgeStep,
  BarChartCategory,
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
    childIds: [],
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

export const pnlRows: PlLineItem[] = [
  { nodeId: 'freight-charter-revenue', label: 'Freight & Charter Revenue', sign: 1, indent: 0 },
  { nodeId: 'voyage-expenses', label: 'Voyage Expenses (bunker, port & canal dues, commissions)', sign: -1, indent: 1 },
  { nodeId: 'vessel-operating-cost', label: 'Vessel Operating Costs (crew, R&M, insurance, stores)', sign: -1, indent: 1 },
  { nodeId: 'gross-profit', label: 'Gross Profit', sign: 1, indent: 0, isSubtotal: true },
  { nodeId: 'depreciation-amortisation', label: 'Depreciation & Amortisation (vessels, drydock)', sign: -1, indent: 1 },
  { nodeId: 'g-and-a-expenses', label: 'General & Administrative Expenses', sign: -1, indent: 1 },
  { nodeId: 'other-operating-income', label: 'Other Operating Income (gain on vessel disposal, etc.)', sign: 1, indent: 1 },
  { nodeId: 'other-operating-expenses', label: 'Other Operating Expenses (impairment, etc.)', sign: -1, indent: 1 },
  { nodeId: 'operating-profit-ebit', label: 'Operating Profit / EBIT', sign: 1, indent: 0, isSubtotal: true },
  { nodeId: 'finance-cost', label: 'Finance Costs (loan & finance lease interest)', sign: -1, indent: 1 },
  { nodeId: 'finance-income', label: 'Finance Income', sign: 1, indent: 1 },
  { nodeId: 'jv-share-profit', label: 'Share of Profit — JV / Pool Arrangements', sign: 1, indent: 1 },
  { nodeId: 'fx-gain-loss', label: 'Foreign Exchange Gain / (Loss)', sign: 1, indent: 1 },
  { nodeId: 'profit-before-tax', label: 'Profit Before Tax', sign: 1, indent: 0, isSubtotal: true },
  { nodeId: 'tax-expense', label: 'Tax Expense', sign: -1, indent: 1 },
  { nodeId: 'npat', label: 'NPAT', sign: 1, indent: 0, isSubtotal: true, isFinal: true },
];

export function formatRmAuto(value: number): string {
  if (Math.abs(value) >= 1000) return `RM${(value / 1000).toFixed(2)}bn`;
  return formatRm(value);
}

export const financialKpis: KpiCard[] = [
  {
    id: 'revenue-ytd',
    label: 'Revenue YTD',
    value: formatRmAuto(vdtNodes['freight-charter-revenue'].actual),
    trend: [92, 95, 97, 101, 108, 112],
  },
  {
    id: 'cost-of-revenue-ytd',
    label: 'Cost of Revenue YTD',
    value: formatRmAuto(rollUp([{ id: 'voyage-expenses', sign: 1 }, { id: 'vessel-operating-cost', sign: 1 }], 'actual')),
    trend: [88, 90, 93, 96, 99, 101],
  },
  {
    id: 'gross-profit-ytd',
    label: 'Gross Profit YTD',
    value: formatRmAuto(vdtNodes['gross-profit'].actual),
    trend: [70, 74, 78, 85, 92, 100],
  },
  {
    id: 'npat-ytd',
    label: 'NPAT YTD',
    value: formatRmAuto(vdtNodes['npat'].actual),
    trend: [60, 64, 70, 78, 88, 96],
  },
];

export const revenueCostOpexChart: BarChartCategory[] = [
  {
    label: 'Revenue',
    actual: vdtNodes['freight-charter-revenue'].actual,
    priorYear: vdtNodes['freight-charter-revenue'].priorYear ?? 0,
  },
  {
    label: 'Cost of Revenue',
    actual: rollUp([{ id: 'voyage-expenses', sign: 1 }, { id: 'vessel-operating-cost', sign: 1 }], 'actual'),
    priorYear: rollUp([{ id: 'voyage-expenses', sign: 1 }, { id: 'vessel-operating-cost', sign: 1 }], 'priorYear'),
  },
  {
    label: 'OPEX',
    actual: rollUp(
      [
        { id: 'depreciation-amortisation', sign: 1 },
        { id: 'g-and-a-expenses', sign: 1 },
        { id: 'other-operating-expenses', sign: 1 },
        { id: 'other-operating-income', sign: -1 },
      ],
      'actual'
    ),
    priorYear: rollUp(
      [
        { id: 'depreciation-amortisation', sign: 1 },
        { id: 'g-and-a-expenses', sign: 1 },
        { id: 'other-operating-expenses', sign: 1 },
        { id: 'other-operating-income', sign: -1 },
      ],
      'priorYear'
    ),
  },
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

/**
 * "Auto-generated" insight pinned above the P&L table: the leaf line with
 * the largest |vs prior year| movement. Recomputed from pnlRows/vdtNodes,
 * not hardcoded, so it can't drift from the table it annotates.
 */
export function getLargestPriorYearMovement(): { label: string; pctLabel: string } {
  const leafRows = pnlRows.filter((r) => !r.isSubtotal);
  let best = leafRows[0];
  let bestPct = -Infinity;
  for (const row of leafRows) {
    const node = vdtNodes[row.nodeId];
    if (!node || node.priorYear === undefined) continue;
    const change = Math.abs(pct(node.actual, node.priorYear));
    if (change > bestPct) {
      bestPct = change;
      best = row;
    }
  }
  const node = vdtNodes[best.nodeId];
  const vsLy = pct(node.actual, node.priorYear ?? node.actual);
  return { label: best.label.replace(/\s*\([^)]*\)\s*$/, ''), pctLabel: formatVar(vsLy) };
}

export function getNode(id: string): VdtNode | undefined {
  return vdtNodes[id];
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

export function formatVar(varPct: number): string {
  const sign = varPct > 0 ? '+' : varPct < 0 ? '' : '±';
  return `${sign}${varPct}%`;
}

export function formatRm(value: number): string {
  return `RM${value.toFixed(1)}m`;
}
