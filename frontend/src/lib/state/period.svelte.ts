/** The most recent of the three fiscal years this prototype seeds — see docs/adr/0032, docs/adr/0051. */
export const DEFAULT_PERIOD_CODE = '2026';

/** The Period chip's current selection — a synthetic Year/Quarter/Month UI id (see period-store.svelte.ts's periodParams for how it maps onto GET /api/financial/tree's ?year=&quarter=&month=). */
let code = $state(DEFAULT_PERIOD_CODE);

export const periodState = {
  get code() {
    return code;
  },
  set(nextCode: string): void {
    code = nextCode;
  },
};
