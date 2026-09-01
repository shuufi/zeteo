# VdtNode becomes GL/FSI-code-keyed, sourced from a new backend endpoint; the hand-authored mock tree is retired

Financial, VDT Explorer, and Driver Diagnostic all read from `vdtNodes`/`pnlRows` in `frontend/src/lib/data/zeteo-data.ts` — a ~90-node tree hand-authored with curated slug ids (`vessel-operating-cost`) and manually-written rollup relationships (`grossProfitRefs`, `ebitRefs`, `pbtRefs`, `npatRefs`). A real SAP GL/FSI hierarchy export exists (`docs/anaplan_is_master_data.csv`, 1171 nodes: 1 reporting root, 87 reporting/subtotal nodes, 1083 posting GL accounts) modelling the same P&L shape at genuine granularity. Rather than layering the real hierarchy alongside the mock one, every screen now reads from a new `GET /api/gl/tree` backend endpoint keyed by real GL codes (`PNL-0024`, `4010100100`, `NPAT`) instead of curated slugs, and the hand-authored ref-list rollup logic is retired in favour of a generic bottom-up tree-walk computed once, server-side, per requested scope.

ADR-0004's single fully-modelled example node (`repairs-maintenance`) is replaced by its real GL/FSI equivalent, `PNL-0024` ("Repairs And Maintenance", under Cost of Revenue — a second, same-named node, `PNL-0037` under G&A Expenses, is not it). Every other node continues to render `NotYetModelled`.

Rejected: keeping the curated tree for VDT Explorer/Driver Diagnostic and only pointing Financial at the real hierarchy — that would leave two permanently-diverging "the P&L hierarchy" concepts and break the existing click-through from a P&L row into VDT Explorer for every GL code that has no curated counterpart.

**Status**: accepted
