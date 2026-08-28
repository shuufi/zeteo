export type Direction = 'adverse' | 'favourable' | 'neutral';

export interface Company {
  code: string;
  name: string;
}

export interface BusinessUnit {
  code: string;
  label: string;
  companies: Company[];
}

export interface KpiCard {
  id: string;
  label: string;
  value: string;
  delta?: string;
  direction?: Direction;
  highlighted?: boolean;
  nodeId?: string;
  trend?: number[];
}

export interface PlLineItem {
  nodeId: string;
  label: string;
  sign: 1 | -1;
  indent: 0 | 1;
  isSubtotal?: boolean;
  isFinal?: boolean;
}

export interface BridgeStep {
  label: string;
  value: number;
  kind: 'total' | 'increase' | 'decrease';
}

export interface BarChartCategory {
  label: string;
  actual: number;
  priorYear: number;
}

export interface ContributionDriver {
  id: string;
  label: string;
  varAbs: number;
  varPct: number;
  direction: Direction;
  rank: number;
}

export interface Sensitivity {
  mostSensitive: string[];
  mostVariable: string[];
}

export interface BenchmarkBar {
  id: string;
  label: string;
  valuePerVod: number;
  kind: 'subject' | 'internal' | 'external';
}

export interface BenchmarkRow {
  basis: string;
  valuePerVod: string;
  gap: string;
}

export interface Benchmark {
  metricLabel: string;
  basis: string;
  bars: BenchmarkBar[];
  rows: BenchmarkRow[];
}

export interface RootCauseEntry {
  id: string;
  driverLabel: string;
  amountLabel: string;
  type: 'FACT' | 'AI_HYPOTHESIS';
  evidenceOrRationale: string;
  mitigation?: string;
  status: 'Validated' | 'AI proposed' | 'Under review' | 'Rejected';
  confidence?: 'Low' | 'Medium' | 'High';
  analystNotes?: string;
}

export interface VdtNode {
  id: string;
  name: string;
  parentId: string | null;
  childIds: string[];
  actual: number;
  budget: number;
  priorYear?: number;
  unit: 'RM_M';
  varPct: number;
  varAbs?: number;
  direction: Direction;
  contributionWidthPct?: number;
  rank?: number;
  hasSummary: boolean;
  hasFullData: boolean;
  trend?: number[];
  drivers?: ContributionDriver[];
  sensitivity?: Sensitivity;
  benchmark?: Benchmark;
  rootCause?: RootCauseEntry[];
  reviewSummary?: string;
}

export interface DriverLink {
  label: string;
  amount: string;
  nodeId?: string;
}

export interface LeadingIndicator {
  label: string;
  value: string;
}

export interface Exception {
  title: string;
  impact: string;
  explainedPct: number;
  targetNodeId: string;
}
