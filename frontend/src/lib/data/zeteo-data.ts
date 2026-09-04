import type { KpiCard, Exception, DriverLink, LeadingIndicator } from './types';

/**
 * Mock context for the whole prototype: vs This Year.
 * The comparison chip renders this but is inert (see docs/adr/0005).
 * Business and Period are live pickers (see docs/adr/0015/0024 and
 * docs/adr/0025/0026) fed by their own endpoints, not this mock.
 */
export const context = {
  comparison: 'vs This Year',
  refreshedAt: '03:00 today',
};

/**
 * Home's illustrative KPIs/exception/drivers are static copy, independent of
 * the GL/FSI tree — see docs/adr/0022. nodeId/targetNodeId values are real
 * GL codes so their links into VDT Explorer/Driver Diagnostic resolve.
 */
export const homeKpis: KpiCard[] = [
  { id: 'cfroa', label: 'CFROA', value: '6.2%', delta: '▼ 0.4pp', direction: 'adverse' },
  { id: 'cffo', label: 'CFFO', value: 'RM412m', delta: '▲ 3.1%', direction: 'favourable' },
  { id: 'npat', label: 'NPAT', value: 'RM188m', delta: '▼ 2.0%', direction: 'adverse' },
  { id: 'revenue', label: 'Revenue', value: 'RM1.06bn', delta: '▲ 1.4%', direction: 'favourable' },
  { id: 'expenses', label: 'Expenses', value: 'RM614m', delta: '▲ 5.2% adv', direction: 'adverse', highlighted: true, nodeId: 'PNL-0030' },
  { id: 'net-assets', label: 'Net Assets', value: 'RM3.9bn', delta: '—', direction: 'neutral' },
];

export const attentionException: Exception = {
  title: 'Repairs & Maintenance +8.4% vs Budget',
  impact: 'RM18.2m adverse impact',
  explainedPct: 72,
  targetNodeId: 'PNL-0024',
};

export const topAdverseDrivers: DriverLink[] = [
  { label: 'Manpower Cost', amount: 'RM9.1m', nodeId: 'PNL-0021' },
  { label: 'Repairs & Maint.', amount: 'RM5.4m', nodeId: 'PNL-0024' },
  { label: 'Fuel (Bunkers)', amount: 'RM3.7m', nodeId: '5110100400' },
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
