type Status = 'idle' | 'loading' | 'ready' | 'error';

let status = $state<Status>('idle');
export interface VarianceAnalysisBullet {
  nodeId: string;
  nodeName: string;
  text: string;
  amount: number;
  deltaPct: number | null;
  contributionPct: number | null;
}

export interface VarianceAnalysisData {
  headline: string;
  netAmount: number;
  bullets: VarianceAnalysisBullet[];
}

let varianceAnalysis = $state<VarianceAnalysisData | null>(null);
let error = $state('');

/**
 * VDT Variance Analysis's narrative panel — on-demand only (see docs/adr/0034),
 * never auto-fetched on period changes. Failure is isolated here: the
 * bridge/table read from vdtComparisonStore independently and keep working
 * whether or not this ever succeeds.
 */
export const varianceAnalysisStore = {
  get status() {
    return status;
  },
  get varianceAnalysis() {
    return varianceAnalysis;
  },
  get error() {
    return error;
  },
  reset(): void {
    status = 'idle';
    varianceAnalysis = null;
    error = '';
  },
};

export async function generateVarianceAnalysis(scope: string, node: string, periodA: string, periodB: string, ytd: boolean): Promise<void> {
  status = 'loading';
  error = '';
  try {
    const params = new URLSearchParams({ scope, node, periodA, periodB, ytd: String(ytd) });
    const res = await fetch(`/api/vdt/variance-analysis?${params}`, { method: 'POST' });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail ?? `Request failed: ${res.status}`);
    }
    const data = await res.json();
    varianceAnalysis = data.varianceAnalysis;
    status = 'ready';
  } catch (err) {
    console.error('Failed to generate VDT variance analysis', err);
    error = err instanceof Error ? err.message : 'Unable to generate variance analysis right now';
    status = 'error';
  }
}
