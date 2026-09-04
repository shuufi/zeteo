type Status = 'idle' | 'loading' | 'ready' | 'error';

let status = $state<Status>('idle');
export interface NarrationBullet {
  nodeId: string;
  nodeName: string;
  text: string;
  amount: number;
}

export interface MovementNarrationData {
  headline: string;
  netAmount: number;
  bullets: NarrationBullet[];
}

let narration = $state<MovementNarrationData | null>(null);
let error = $state('');

/**
 * VDT Statement's movement narration — on-demand only (see docs/adr/0034),
 * never auto-fetched on period changes. Failure is isolated here: the
 * bridge/table read from vdtComparisonStore independently and keep working
 * whether or not this ever succeeds.
 */
export const narrationStore = {
  get status() {
    return status;
  },
  get narration() {
    return narration;
  },
  get error() {
    return error;
  },
  reset(): void {
    status = 'idle';
    narration = null;
    error = '';
  },
};

export async function generateNarration(scope: string, node: string, periodA: string, periodB: string, ytd: boolean): Promise<void> {
  status = 'loading';
  error = '';
  try {
    const params = new URLSearchParams({ scope, node, periodA, periodB, ytd: String(ytd) });
    const res = await fetch(`/api/vdt/narration?${params}`, { method: 'POST' });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail ?? `Request failed: ${res.status}`);
    }
    const data = await res.json();
    narration = data.narration;
    status = 'ready';
  } catch (err) {
    console.error('Failed to generate VDT movement narration', err);
    error = err instanceof Error ? err.message : 'Unable to generate narration right now';
    status = 'error';
  }
}
