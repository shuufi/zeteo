# VDT Statement renamed to VDT Comparison and moved off bare `/vdt`

VDT Statement (ADR-0034) lived at `/vdt`, under the "Explorer" nav label — the same URL/label the Value Driver dropdown uses for the whole browsing family (Ranked, Tree, Diagnostic). But VDT Statement's default and primary behavior, since ADR-0034, is a two-period comparison: a delta bridge, a Period A/B/Delta table, and on-demand movement narration. A user clicking "Explorer" expecting to browse the VDT hierarchy instead lands on a period-comparison screen. This ADR renames the page and gives it its own route and nav entry, separate from Explorer.

## Decision

- **Route**: the page moves from `/vdt` to `/vdt/compare`. Bare `/vdt` becomes a redirect to `/vdt/compare` (`VdtExplorerRedirect.svelte`, client-side `replace()` via `svelte-spa-router` — no server round-trip, no history entry added).
- **Nav**: the Value Driver dropdown gains a third child, **"Comparison"** (href `/vdt/compare`), sitting alongside the existing "Explorer" and "Reconciliation" children. "Explorer"'s `activePath` regex excludes `/vdt/compare` the same way it already excludes `/vdt/reconciliation`.
- **Label**: "Comparison" is deliberately reused across hierarchies, mirroring the existing Financial dropdown (`/financial` = "Trends", `/financial/compare` = "Comparison"). Value Driver's dropdown now follows the same shape: Explorer/Comparison/Reconciliation. This explicitly supersedes ADR-0034/CONTEXT.md's earlier guidance to avoid the word "Comparison" for this screen (which was defending against confusion with `/financial/compare`) — the two screens now share a label pattern on purpose, distinguished by which hierarchy/nav branch they're under, the same way "Trends" is not assumed to be one single screen just because both Financial and (eventually) Explorer might use a similar term.
- **Component**: `VdtStatement.svelte` is renamed to `VdtComparison.svelte`. Its `PageHeader` title changes from "Value Driver" to "VDT Comparison". No behavioral change — same Cost Bridge, statement table, comparison modes, and movement narration as ADR-0034 defined.

## Explorer's landing page

This does not give Explorer (Ranked/Tree) a landing page of its own — that's real, separate future work. Until it exists, `/vdt`'s redirect to `/vdt/compare` means clicking "Explorer" in the nav still surfaces the Comparison screen, reintroducing the original mislabeling temporarily. This is accepted as a known, deliberate interim state: the alternative (hiding the "Explorer" nav item until its landing exists) would remove the only nav-level entry point into Ranked/Tree, which is worse.

## Considered and rejected

**Renaming "Explorer" itself instead of splitting out a new screen**: rejected — Ranked and Tree are genuinely browse/drill-down screens with no comparison behavior; renaming the whole family to reflect one page's behavior would mislabel the other two.

**Splitting VdtStatement.svelte into two components now** (a real Explorer landing + a Comparison screen): rejected as out of scope for this change — deferred to whenever Explorer's landing page is actually built, to avoid renaming/touching this file twice.

**Distinct label ("Compare" vs "Comparison") to avoid any visual echo of `/financial/compare`**: rejected — once duplicate labels across hierarchies were established as acceptable (see Financial's own Trends/Comparison precedent), a deliberately different label would be inconsistency for its own sake.

**Status**: accepted
