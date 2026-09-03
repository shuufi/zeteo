// Only company 0190 carries fabricated fact data (see docs/adr/0032) — every
// other scope renders Not-yet-modelled, so this is the only sensible default.
/** The Business chip's current selection — a company or BU code passed as GET /api/gl/tree's ?scope=. */
let code = $state('0190');
let label = $state('MISC Ship Management Sdn. Bhd.');

export const scopeState = {
  get code() {
    return code;
  },
  get label() {
    return label;
  },
  set(nextCode: string, nextLabel: string): void {
    code = nextCode;
    label = nextLabel;
  },
};
