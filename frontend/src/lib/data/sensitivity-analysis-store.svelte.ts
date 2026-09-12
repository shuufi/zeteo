import type { SensitivityCandidate, SensitivityProgress, SensitivityResult } from './types';
import { periodParams } from './period-store.svelte';

type Status = 'idle' | 'streaming' | 'ready' | 'error';

let status = $state<Status>('idle');
let progress = $state<SensitivityProgress | null>(null);
let result = $state<SensitivityResult | null>(null);
let error = $state('');
// Candidates as their own results land mid-run, in arrival order — not
// ranked/truncated (rank order isn't stable until every candidate's in,
// see vdt_sensitivity.py's compute_sensitivity docstring). The route derives
// a provisional top-N from this for a progressively-filling tornado chart;
// once `result` lands, that authoritative ranked/candidates list takes over.
let liveCandidates = $state<SensitivityCandidate[]>([]);

// Held module-level (not component-local) so a second startSensitivity()
// call — or a route navigation away mid-run — can abort whatever's still
// in flight, the same "on-demand, isolated failure" shape as Variance/Trend
// Analysis, plus cancellation for this screen's longer-running SSE stream.
let controller: AbortController | null = null;

/**
 * VDT Sensitivity Analysis's on-demand elasticity run — see docs/adr/0043.
 * Never auto-fetched (button-triggered only); progress/result/error are
 * independent of vdtStore, which the route reads separately for its scope
 * picker tree.
 */
export const sensitivityStore = {
  get status() {
    return status;
  },
  get progress() {
    return progress;
  },
  get result() {
    return result;
  },
  get error() {
    return error;
  },
  get liveCandidates() {
    return liveCandidates;
  },
  reset(): void {
    controller?.abort();
    controller = null;
    status = 'idle';
    progress = null;
    result = null;
    error = '';
    liveCandidates = [];
  },
};

/**
 * `window` mirrors the backend's mutually-exclusive `year`/`trailingEnd`
 * params (see docs/adr/0042) — Financial Year mode passes a Year code,
 * Trailing mode passes the anchor Month code.
 */
export async function startSensitivity(req: {
  scope: string;
  scopeNode: string;
  bumpPct: number;
  source: 'actual' | 'budget';
  window: { year: string } | { trailingEnd: string };
}): Promise<void> {
  controller?.abort();
  controller = new AbortController();
  const { signal } = controller;

  status = 'streaming';
  progress = { completed: 0, total: 0 };
  result = null;
  error = '';
  liveCandidates = [];

  const windowPayload = (() => {
    if ('trailingEnd' in req.window) {
      const { year, month } = periodParams(req.window.trailingEnd);
      return { trailingEndYear: year, trailingEndPeriod: month };
    }
    return { year: periodParams(req.window.year).year };
  })();

  const payload = {
    scope: req.scope,
    scopeNode: req.scopeNode,
    bumpPct: req.bumpPct,
    source: req.source,
    ...windowPayload,
  };

  try {
    const res = await fetch('/api/vdt/sensitivity', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal,
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail ?? `Request failed: ${res.status}`);
    }
    if (!res.body) throw new Error('No response body');

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const frames = buffer.split('\n\n');
      buffer = frames.pop() ?? '';
      for (const frame of frames) {
        const line = frame.trim();
        if (!line.startsWith('data: ')) continue;
        const event = JSON.parse(line.slice('data: '.length));
        if (event.type === 'progress') {
          progress = { completed: event.completed, total: event.total };
        } else if (event.type === 'candidate') {
          liveCandidates = [...liveCandidates, event.candidate as SensitivityCandidate];
        } else if (event.type === 'result') {
          result = event as SensitivityResult;
          status = 'ready';
        } else if (event.type === 'error') {
          error = event.detail ?? 'Unable to run sensitivity analysis right now';
          status = 'error';
        }
      }
    }
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') return; // user navigated / restarted — swallow silently
    console.error('Failed to run VDT sensitivity analysis', err);
    error = err instanceof Error ? err.message : 'Unable to run sensitivity analysis right now';
    status = 'error';
  }
}
