import type { VdtNode } from './types';

export interface GlScopeMeta {
  scope: string;
  scopeKind: 'company' | 'bu';
  partial: boolean;
  sampledCompanyCount: number;
  totalCompanyCount: number;
}

type Status = 'loading' | 'ready' | 'error' | 'not-yet-modelled';

let tree = $state<Record<string, VdtNode>>({});
let status = $state<Status>('loading');
let meta = $state<GlScopeMeta | null>(null);

export const glStore = {
  get tree() {
    return tree;
  },
  get status() {
    return status;
  },
  get meta() {
    return meta;
  },
};

export async function loadScope(scope: string): Promise<void> {
  status = 'loading';
  try {
    const res = await fetch(`/api/gl/tree?scope=${encodeURIComponent(scope)}`);
    if (!res.ok) throw new Error(`Request failed: ${res.status}`);
    const data = await res.json();
    if (data.notYetModelled) {
      tree = {};
      meta = null;
      status = 'not-yet-modelled';
      return;
    }
    tree = data.nodes;
    meta = {
      scope: data.scope,
      scopeKind: data.scopeKind,
      partial: data.partial,
      sampledCompanyCount: data.sampledCompanyCount,
      totalCompanyCount: data.totalCompanyCount,
    };
    status = 'ready';
  } catch (err) {
    console.error('Failed to load GL tree', err);
    status = 'error';
  }
}
