# VDT Statement renamed to VDT Comparison (later VDT Variance Analysis) and moved off bare `/vdt`

VDT Statement (ADR-0034) lived at `/vdt`, under the "Explorer" nav label — the same URL/label the Value Driver dropdown uses for the whole browsing family (Ranked, Tree, Diagnostic). But VDT Statement's default and primary behavior, since ADR-0034, is a two-period comparison: a delta bridge, a Period A/B/Delta table, and on-demand movement narration. A user clicking "Explorer" expecting to browse the VDT hierarchy instead lands on a period-comparison screen. This ADR renames the page and gives it its own route and nav entry, separate from Explorer.

**Update**: the page and its narrative panel were renamed a second time, from VDT Comparison / Movement Narration to **VDT Variance Analysis** / **Variance Analysis** — see "Second rename" below. The Decision section is edited in place to describe the current (post-rename) state rather than preserved as of the original VDT Statement → VDT Comparison move.

## Decision

- **Route**: the page moves from `/vdt` to `/vdt/variance` (originally `/vdt/compare` — see "Second rename"). Bare `/vdt` becomes a redirect to `/vdt/variance` (`VdtExplorerRedirect.svelte`, client-side `replace()` via `svelte-spa-router` — no server round-trip, no history entry added).
- **Nav**: the Value Driver dropdown gains a third child, **"Variance"** (href `/vdt/variance`; originally "Comparison" at `/vdt/compare`), sitting alongside the existing "Explorer" and "Reconciliation" children. "Explorer"'s `activePath` regex excludes `/vdt/variance` the same way it already excludes `/vdt/reconciliation`.
- **Label**: "Comparison" was originally deliberately reused across hierarchies, mirroring the existing Financial dropdown (`/financial` = "Trends", `/financial/compare` = "Comparison") — see "Second rename" for why the nav label later became "Variance" instead.
- **Component**: `VdtStatement.svelte` was renamed to `VdtComparison.svelte`, then to `VdtVarianceAnalysis.svelte` (see "Second rename"). Its `PageHeader` title is "VDT Variance Analysis" (originally "Value Driver", then "VDT Comparison"). No behavioral change from either rename — same Cost Bridge, statement table, comparison modes, and narrative panel as ADR-0034 defined.

## Second rename: VDT Comparison → VDT Variance Analysis

The page's default/primary content is (and always was, since ADR-0034) a period-over-period *variance* view — a delta bridge plus an LLM narrative explaining what drove the movement. "Comparison" named the *mechanism* (two periods, A vs B) rather than *what the page is for* (surfacing and explaining variance); "Variance Analysis" names the latter and also gives the narrative panel — previously "Movement Narration" — a name that matches the page it lives on, the same way VDT Trends' narrative panel is called "Trend Analysis" (ADR-0040).

- **Route**: `/vdt/compare` → `/vdt/variance`. No redirect from the old path — this is an internal tool with no external bookmarking guarantees, unlike the bare-`/vdt` redirect above (which exists because "Explorer" is a permanent nav entry point, not a renamed leaf route).
- **Nav label**: "Comparison" → "Variance" (short form; full "VDT Variance Analysis" appears in the `PageHeader`, mirroring how "Explorer"/"Reconciliation" are short nav words while their pages carry the full title).
- **Component/file renames**: `VdtComparison.svelte` → `VdtVarianceAnalysis.svelte`; `MovementNarration.svelte` → `VarianceAnalysis.svelte`; `narration-store.svelte.ts` → `variance-analysis-store.svelte.ts` (`narrationStore`/`generateNarration`/`NarrationData` → `varianceAnalysisStore`/`generateVarianceAnalysis`/`VarianceAnalysisData`); `backend/narration.py` → `backend/variance_analysis.py` (`generate_narration`/`NarrationUnavailable`/`build_prompt` → `generate_variance_analysis`/`VarianceAnalysisUnavailable`/`build_variance_analysis_prompt`).
- **Endpoint**: `POST /api/vdt/narration` → `POST /api/vdt/variance-analysis`; response key `"narration"` → `"varianceAnalysis"`. No change to the request/response shape otherwise, no cache-key change.
- **Not renamed**: `ContextBar.svelte`'s `showComparison`/`vdtComparison`/`vdtComparisonMode`/`showComparisonChip` props and `vdt-comparison-store.svelte.ts` — these name the generic two-period-diff UI mechanism shared with other screens (e.g. VDT Trends' comparison chip), not this page specifically, and stay as "Comparison".

## Explorer's landing page

This does not give Explorer (Ranked/Tree) a landing page of its own — that's real, separate future work. Until it exists, `/vdt`'s redirect to `/vdt/variance` means clicking "Explorer" in the nav still surfaces the Variance Analysis screen, reintroducing the original mislabeling temporarily. This is accepted as a known, deliberate interim state: the alternative (hiding the "Explorer" nav item until its landing exists) would remove the only nav-level entry point into Ranked/Tree, which is worse.

## Considered and rejected

**Renaming "Explorer" itself instead of splitting out a new screen**: rejected — Ranked and Tree are genuinely browse/drill-down screens with no comparison behavior; renaming the whole family to reflect one page's behavior would mislabel the other two.

**Splitting VdtStatement.svelte into two components now** (a real Explorer landing + a Comparison screen): rejected as out of scope for this change — deferred to whenever Explorer's landing page is actually built, to avoid renaming/touching this file twice.

**Distinct label ("Compare" vs "Comparison") to avoid any visual echo of `/financial/compare`**: rejected — once duplicate labels across hierarchies were established as acceptable (see Financial's own Trends/Comparison precedent), a deliberately different label would be inconsistency for its own sake.

**Status**: accepted
