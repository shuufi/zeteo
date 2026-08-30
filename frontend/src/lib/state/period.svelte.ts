/** The single fiscal year this whole prototype seeds — see docs/adr/0025. */
export const DEFAULT_PERIOD_CODE = 'FY26';

/** The Period chip's current selection — a Year/Quarter/Month code passed as GET /api/gl/tree's ?period=. */
let code = $state(DEFAULT_PERIOD_CODE);

export const periodState = {
  get code() {
    return code;
  },
  set(nextCode: string): void {
    code = nextCode;
  },
};
