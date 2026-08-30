import { periodState } from './period.svelte';

let dirty = $state(false);
let code = $state(periodState.code);

/** The Period picker's pending selection — see scope-draft.svelte.ts for why this is separate from periodState. */
export const periodDraft = {
  get code() {
    return dirty ? code : periodState.code;
  },
  get dirty() {
    return dirty;
  },
  set(nextCode: string): void {
    dirty = true;
    code = nextCode;
  },
  reset(): void {
    dirty = false;
  },
};
