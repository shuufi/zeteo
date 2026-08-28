# Financial Performance is its own nav item and route, not a VDT Explorer view mode

Design 2a introduced a full-P&L overview screen, framed in the wireframe as "VDT Explorer's landing state, before drilling into a line." Rather than folding it into VDT Explorer as a third view mode (alongside Ranked and Tree), it became its own top-level nav item and route — **Financial Performance** at `/financial` — with VDT Explorer's existing entry point renamed **Value Driver** and left at `/vdt/expenses`. Financial Performance's nav item is active only on `/financial` itself; Value Driver's stays active across the whole `/vdt/*`, `/vdt-tree/*`, `/diagnostic/*` journey, since that's the branch the IA doc (wireframe option 1a) already treats as one continuous flow. This was an explicit user decision during scoping, not a default.

Two consequences for `frontend/src/lib/data/zeteo-data.ts`:

1. **Reuse existing nodes, don't fork the data.** Two P&L statement lines collide by name with nodes already wired elsewhere in the app — `vessel-operating-cost` (Home's exception card, Value Driver) and `finance-cost` (under Expenses). Rather than duplicating them with the wireframe's mockup figures, the P&L statement reuses the existing nodes' real actual/budget/prior-year values. Every other line (Revenue, Gross Profit, D&A, Tax, NPAT, etc.) has no existing counterpart, so it's a new `VdtNode` using the mockup's figures.
2. **Subtotals are computed, not stored.** Because two inputs now come from the app's real (smaller) figures instead of the mockup's, Gross Profit / EBIT / Profit Before Tax / NPAT no longer equal the wireframe's hardcoded totals. Rather than hand-typing subtotal numbers that would silently drift out of sync with their own children, `buildSubtotal()` sums each subtotal's contributing nodes live — one source of truth, at the cost of the shipped numbers no longer pixel-matching the design doc.

Every P&L line — leaf or subtotal — gets a real `nodeId` and routes to `/vdt/:id`; per `docs/adr/0004-mock-data-depth.md`, lines with no further decomposition fall through to `NotYetModelled` rather than dead-ending.

**Status**: accepted
