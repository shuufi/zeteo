# VDT Trends becomes Explorer's real landing page

ADR-0038 moved VDT Comparison off bare `/vdt` to `/vdt/compare`, but left `/vdt` as a client-side redirect to it (`VdtExplorerRedirect.svelte`), explicitly deferring Explorer's own landing page as "real, separate future work." This ADR builds that landing page: a VDT-hierarchy statement table showing all 12 months of a fiscal year at once, closing the gap ADR-0038 left open.

## Decision

- **Route**: `VdtTrends.svelte` renders directly at `/vdt` (no redirect). `VdtExplorerRedirect.svelte` is deleted.
- **Nav**: the Value Driver dropdown's first child is renamed from "Explorer" to **"Trends"** (href unchanged, `/vdt`) — mirroring Financial's Trends/Comparison split (`/financial` = Trends, `/financial/compare` = Comparison) the same way VDT Comparison's own "Comparison" label already does (ADR-0038). Ranked (`/vdt/:id`) and Tree (`/vdt-tree`) stay nav-invisible, reached only by drill-down — unchanged from before.
- **Hierarchy root**: same fixed pilot scope as VDT Comparison and Reconciliation, `V201000000` (SOC Crew Cost). No node picker — none exists for the VDT hierarchy yet (ADR-0037).
- **Body**: table only, no charts. Reuses `buildDisplayRows` at full hierarchy depth (same function VDT Comparison's own table already uses), 12 monthly columns for the picked fiscal year, per-cell drill-down links into Ranked (`/vdt/:id?period=...`), and the "Show code" toggle — all the same idioms VDT Comparison's plain-mode table already established. No Cost Bridge waterfall and no monthly trend line chart: a 12-column table already shows month-over-month movement, and a single-period bridge doesn't fit a screen whose point is seeing all 12 months at once.
- **Context Bar**: five controls — Company (always-on `BusinessPicker`), a new Actual/Budget data-selection chip, a new Year-only Period picker, YTD, and Monetary display scale. No comparison chip, no VDT comparison mode.

## Actual/Budget and the monthly-budget data gap

`HierarchyNode` (the shape both the Accounting and VDT trees use) has `monthlyActual` and `monthlyPriorYear` arrays but only an annual `budget` scalar — no `monthlyBudget` array exists yet on either hierarchy. Rather than fake a flat `budget/12` spread (misleading for seasonal spend) or hide the option until the backend catches up (the context bar explicitly calls for a live Actual/Budget selector), the chip is real and live: picking "Budget" simply renders every cell as `null`, which `StatementTable` already displays as `—` (its existing "not comparable" convention — see `docs/adr/0034`'s cell-value handling). No new UI state, no special-cased empty message — this is the same convention already used for "no same-code counterpart" cells elsewhere, applied to a genuinely-missing data case.

This is a known, deliberate v1 gap: adding a real `monthlyBudget` series to both trees' backend endpoints is separate, future work. Once it lands, wiring it into this chip's `cellValue` branch is a small, additive change.

## Year-only Period picker

`PeriodPicker` gained a `yearOnly` prop (threaded through a new `ContextBar` `periodYearOnly` prop) that lists only the three fiscal-year sibling roots, with no Quarter/Month drill-down — selecting a year commits and closes immediately, the same way selecting a leaf period already did. This reuses the existing `periodStore`/`periodDraft`/Apply-button plumbing rather than forking a parallel component; the alternative (letting users drill into a Quarter/Month that the page then silently resolves back up to its parent year) would expose dead, misleading UI.

## Considered and rejected

**A monthly trend line chart** (`MonthlyTrendChart`, matching Accounting Trends' KPI-line chart): rejected — a 12-column table already shows the same information, and building a chart with no new information over the table would be pure visual overhead for this change.

**A single-period Cost Bridge waterfall** (matching VDT Comparison's plain-mode branch): rejected — inherently anchored to one month, which doesn't fit a screen whose entire point is showing all twelve at once, and would need a second, unrelated period concept the context bar doesn't otherwise have.

**Disabling the Budget chip option** (grayed out, unselectable, "coming soon"): rejected — building and then later un-building a disabled-state control is throwaway work; a live selector that renders the existing not-comparable dash is simpler now and needs no follow-up UI change once real data lands.

**Status**: accepted
