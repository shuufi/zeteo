# VDT Trends gains a Trailing window alongside Financial Year

ADR-0039 gave VDT Trends a single Period control: a Year-only picker showing all 12 months of whichever fiscal year is selected. That's the only way to see a trend today — a user comparing Q4 of one fiscal year against Q1 of the next has to flip between two Year selections and reconcile the seam themselves. This ADR adds a second mode, **Trailing**, that shows a 12-month window ending at a user-picked anchor month, sliding freely across the FY24/FY25/FY26 sibling-root boundary established by ADR-0032.

Scoped to VDT Trends only. VDT Variance Analysis (`/vdt/variance`) and Reconciliation (`/vdt/reconciliation`) are untouched — they're two-period-diff and point-in-time screens respectively, not statement-over-time screens, and keep their existing pickers.

Called **Trailing**, not "Rolling" — "Rolling" is reserved for forecasting (e.g. a rolling forecast), and this feature never forecasts, it only ever looks backward over closed/seeded actuals.

## Decision

**Mode selector.** VDT Trends' Period control becomes two modes: **Financial Year** (today's Year-only picker, unchanged) and **Trailing** (new: pick one anchor month, window = that month plus the 11 preceding months). Default mode on landing is Financial Year — no behavior change for existing bookmarks/links. Switching to Trailing for the first time defaults its anchor to the latest month of the latest fiscal year (`FY26-M12`).

**Anchor picker has no lower bound.** A user can pick any month as the anchor, including one close to the earliest seeded data (`FY24-M01`), which produces a **partial window** of fewer than 12 months. This is deliberate, not an oversight: production will start from zero operational history and grow month by month, so the UI needs to degrade gracefully to "as many months as exist" rather than refusing to render until 12 are available. No enforced minimum window size either — a 1-month window is allowed, and simply produces no month-over-month figures (nothing precedes it to diff against).

**Column labels.** Trailing mode's columns use a calendar-style short label (`Sep '25`), not the `FY##-M##` code Financial Year mode implicitly relies on via the Year picker's framing — a bare month name would be ambiguous once a window can repeat a month name across two fiscal years (e.g. two different `Sep`s). This is a pure frontend reformat of the existing `"Sep FY25"` period label (fiscal years are calendar-aligned, Jan start, per `backend/seed.py`'s `FISCAL_YEARS`/`MONTH_LABELS`) — no new backend data.

**Cumulative toggle (renamed from YTD).** The existing YTD cumulative-sum toggle is renamed **Cumulative** and its base redefined per mode: cumulative-from-fiscal-year-start in Financial Year mode (unchanged behavior, relabeled), cumulative-from-window-start in Trailing mode. "YTD" is retired as a label everywhere on this screen since "year to date" has no meaning for an arbitrary trailing window; "Cumulative" is the mode-agnostic replacement.

**Budget scenario allowed across the FY seam.** Budget figures are prorated per fiscal year from an annual baseline (`backend/seed.py`'s `prorate()`), so a Trailing window crossing two fiscal years stitches two different annual budget baselines into one series. This is allowed without any UI caveat or visual flag — treated the same as Actual. The discontinuity, if visually apparent, is accurate to how the two years were actually planned independently; hiding or flagging it would imply a problem that isn't one.

**Trend Analysis narrative extends to Trailing mode.** The LLM narrative (ADR-0040) works in both modes. No forced caveat text is injected for FY-crossing or partial windows — the prompt receives accurate window metadata (real dates, real month count) and narrates naturally; if a budget-baseline jump or short series is materially significant, the existing deterministic MoM/root-share flagging in `trend_flagging.py` surfaces it like any other flagged movement, same as it would within a single fiscal year.

## Backend: generalizing away from a single Year param

`POST /api/vdt/trend-analysis` takes a single `year` period code today; `build_vdt_tree` → `load_monthly` → `month_codes_of_year` all resolve a Year row's 12 Month children, and `DriverEngine` is constructed with that same single `year_code` (`backend/gl_tree.py:355`). None of this is expressible as "the 12 months belong to one Year."

Generalized instead to take an explicit **list of month period codes** (12 or fewer):
- Financial Year mode passes a Year's children unchanged (same call shape as today, functionally a no-op change).
- Trailing mode resolves N month codes by walking backward from the anchor via each Period's `order`, crossing into the prior fiscal year's sibling root when the current one is exhausted.
- `DriverEngine` needs the same generalization — it's currently built from one `year_code`, and must accept the same explicit month-code list so Driver Formula evaluation stays consistent across a window that spans two Year rows.
- `trend_flagging.py`'s `flag_trends` hardcodes `range(1, 12)` when scanning for month-over-month movement; this becomes `range(1, len(series))` to support partial (< 12 month) windows without a separate code path.
- The narrative cache key (`main.py:266`, currently `(scope, year, scenario)`) is rekeyed on the resolved window (e.g. the anchor month code plus window length) rather than a bare year code, so Financial Year and Trailing requests that happen to resolve to the same 12 months share a cache entry.

## Considered and rejected

**Keeping `build_vdt_tree(year)` as-is and adding a separate trailing-specific fetch/stitch function**: rejected — GLFact/DriverFact rows are already keyed by month `period_code`, not by Year, so the Year param was only ever a convenience for "these 12 month codes." A second function duplicating that resolution logic is unnecessary maintenance surface for what's really one query shape either way.

**Auto-anchoring Trailing mode to "the latest actual month"** (a rolling-forecast-style cursor): rejected — the seeded dataset populates all 12 months of every fiscal year as "actual" uniformly; there's no actual-vs-not-yet-happened distinction in this data model to anchor to. The anchor is a plain user-picked month instead.

**Enforcing a minimum window size (e.g. 3 months) before MoM/narrative logic runs**: rejected — production's real bootstrapping path will start with 0-1 months of history and grow; special-casing the demo to require more than that would need to be undone again once real ingestion begins. Graceful degradation (fewer flags, shorter charts, natural narrative) is preferred over a hard floor.

**Deferring the Trend Analysis narrative to a later pass, shipping Trailing mode as table+chart only for now**: considered, but rejected in favor of shipping both together — the narrative's prompt only needs accurate window metadata, not new business logic, so there's no meaningful scope-reduction benefit to splitting it out.

**Status**: accepted
