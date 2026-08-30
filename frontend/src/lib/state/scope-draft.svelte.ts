import { scopeState } from './scope.svelte';

let dirty = $state(false);
let code = $state(scopeState.code);
let label = $state(scopeState.label);

/**
 * The Business picker's pending selection — separate from scopeState (the
 * scope GET /api/gl/tree actually uses) so picking a company doesn't refetch
 * data until ContextBar's Apply button commits it. Mirrors scopeState until
 * the user picks something (`dirty`), so it can't go stale against a scope
 * change applied elsewhere — e.g. Apply itself, or a deep-link.
 */
export const scopeDraft = {
  get code() {
    return dirty ? code : scopeState.code;
  },
  get label() {
    return dirty ? label : scopeState.label;
  },
  get dirty() {
    return dirty;
  },
  set(nextCode: string, nextLabel: string): void {
    dirty = true;
    code = nextCode;
    label = nextLabel;
  },
  reset(): void {
    dirty = false;
  },
};
