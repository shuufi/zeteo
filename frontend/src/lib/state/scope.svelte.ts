/** The Business chip's current selection — a company or BU code passed as GET /api/gl/tree's ?scope=. */
let code = $state('AET');
let label = $state('AET');

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
