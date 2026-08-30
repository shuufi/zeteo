import type { CompanyNode } from './types';

type Status = 'loading' | 'ready' | 'error';

let tree = $state<Record<string, CompanyNode>>({});
let status = $state<Status>('loading');

export const companyStore = {
  get tree() {
    return tree;
  },
  get status() {
    return status;
  },
};

/** The Group/BU/Company hierarchy is static master data — fetched once, unlike loadScope. */
export async function loadCompanies(): Promise<void> {
  status = 'loading';
  try {
    const res = await fetch('/api/companies');
    if (!res.ok) throw new Error(`Request failed: ${res.status}`);
    tree = await res.json();
    status = 'ready';
  } catch (err) {
    console.error('Failed to load companies', err);
    status = 'error';
  }
}
