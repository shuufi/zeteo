type Status = 'idle' | 'loading' | 'ready' | 'error';

export interface TrendDriver {
  name: string;
  unit: string;
  series: number[];
  expression?: string | null;
}

export interface TrendFlaggedMonth {
  monthIndex: number;
  prevValue: number;
  currValue: number;
  momPct: number | null;
  direction: 'increased' | 'decreased' | 'unchanged';
  sharePct: number;
}

export interface TrendBullet {
  nodeId: string;
  nodeName: string;
  nodeType: string;
  text: string;
  series: number[];
  rootSeries: number[];
  flaggedMonths: TrendFlaggedMonth[];
  peakMonthIndex: number;
  amount: number;
  drivers: TrendDriver[];
}

export interface TrendAnalysisData {
  headline: string;
  scenario: 'actual' | 'budget';
  bullets: TrendBullet[];
}

let status = $state<Status>('idle');
let analysis = $state<TrendAnalysisData | null>(null);
let error = $state('');

/**
 * VDT Trends' on-demand Trend Analysis narrative — see docs/adr/0040. Never
 * auto-fetched, same rationale as Variance Analysis (docs/adr/0034): fails
 * independently of the statement table, which reads from vdtStore and keeps
 * working whether or not this ever succeeds.
 */
export const trendAnalysisStore = {
  get status() {
    return status;
  },
  get analysis() {
    return analysis;
  },
  get error() {
    return error;
  },
  reset(): void {
    status = 'idle';
    analysis = null;
    error = '';
  },
};

/**
 * `window` mirrors the backend's mutually-exclusive `year`/`trailingEnd`
 * params (see docs/adr/0042) — Financial Year mode passes a Year code,
 * Trailing mode passes the anchor Month code.
 */
export async function generateTrendAnalysis(
  scope: string,
  scenario: 'actual' | 'budget',
  window: { year: string } | { trailingEnd: string },
): Promise<void> {
  status = 'loading';
  error = '';
  try {
    const params = new URLSearchParams({ scope, scenario });
    if ('trailingEnd' in window) {
      params.set('trailingEnd', window.trailingEnd);
    } else {
      params.set('year', window.year);
    }
    const res = await fetch(`/api/vdt/trend-analysis?${params}`, { method: 'POST' });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail ?? `Request failed: ${res.status}`);
    }
    const data = await res.json();
    analysis = data.trendAnalysis;
    status = 'ready';
  } catch (err) {
    console.error('Failed to generate VDT trend analysis', err);
    error = err instanceof Error ? err.message : 'Unable to generate trend analysis right now';
    status = 'error';
  }
}
