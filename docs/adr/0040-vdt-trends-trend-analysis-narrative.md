# VDT Trends gains an LLM-generated Trend Analysis narrative

ADR-0034 gave VDT Variance Analysis an on-demand LLM narrative explaining the movement between two periods (Variance Analysis). VDT Trends (`/vdt`, ADR-0039) has no narrative at all — its statement table shows all 12 months at once but leaves the reader to spot what actually moved and why. This ADR adds that narrative, scoped to the shape of a 12-month trend rather than a two-point diff.

## Decision

**Name**: "Trend Analysis" — a distinct concept from Variance Analysis: Variance Analysis explains a delta between two chosen periods; Trend Analysis scans a full fiscal year for what stands out.

**Trigger and placement**: an on-demand button (never auto-fired, same rationale as ADR-0034) placed above VDT Trends' statement table, in a width-capped card rather than stretched full-width like the table — the table's 12-column width doesn't suit a prose narrative.

**Scope**: whole-tree, one button for the page — not a per-row "explain this line" action. Matches VDT Trends' own framing (ADR-0039): the point of this screen is seeing everything at once, so the narrative scans everything at once too.

**Baseline**: month-over-month only. VDT Trends has no second-period picker to diff against (unlike VDT Variance Analysis), and MoM is the only baseline that fits "trends across the month" — YoY or budget-baseline comparisons are a different feature, not this one.

**YTD toggle is display-only here**: Trend Analysis always reads the underlying monthly (non-cumulative) `monthlyActual`/`monthlyBudget` series regardless of what the YTD toggle currently shows on-screen. A cumulative series trends monotonically by construction, which would make MoM anomaly detection meaningless; the toggle keeps scoping only the table's display, not the narrative's input data.

**Actual/Budget dimension**: Trend Analysis works on whichever series the context bar's Actual/Budget chip currently selects. This closes part of the gap ADR-0039 left open — `build_vdt_tree()` gains a `monthlyBudget` array computed the same way `monthlyActual` already is, via `DriverEngine` with `scenario="budget"` instead of `scenario="actual"` (the underlying `DriverFact` rows already carry a scenario dimension and are seeded for both `actual` and `budget` across all fiscal years — this is wiring, not new data modelling). The Budget chip's dash-for-null behavior (ADR-0039) stays in place at the table level for any other consumer not yet updated to use this array.

**Anomaly detection is server-side, not the LLM's job**: a node is flagged when its MoM change exceeds **15%** AND its magnitude exceeds **5% of the root's total value** for that month — both computed in Python before the prompt is built. This mirrors ADR-0034's principle (the LLM narrates given facts, it doesn't compute its own arithmetic) extended to flagging: the LLM never decides what's material, it only explains what the backend already flagged as material. Both constants are named, tunable values, not embedded in prompt text — expected to move once real data shows what's noisy vs. meaningful.

**Detect on dollar impact, explain via operational driver**: flagging ranks by dollar-impact movement on GL leaves / Posting Activity Accounts (a driver moving 50% on a trivial line isn't big-ticket). The narration text for each flagged item then drills into its Driver Formula's terms — e.g. crew headcount, travel/crew-movement counts, salary or accommodation rates — to explain *why* it moved, the same "quantity vs. rate" attribution ADR-0034 established. This directly answers the ask that drove this feature: emphasize the operational driver behind a movement, not just the financial outcome number.

**Prompt payload is flagged nodes only, not the whole tree**: unlike Variance Analysis (ADR-0034), which sends its whole subtree unpruned because it's a single subtree at two points, Trend Analysis spans 12 months across a whole tree — sending everything would make the payload large and let the LLM narrate things the backend never flagged as significant. Each flagged node's prompt entry carries its 12-month series, its parent/root context (for a "% of total" framing), and its Driver Formula terms' own 12-month series — the same per-node shape ADR-0034 uses, just windowed to flagged nodes and widened from 2 values to 12.

**Output shape**: one headline plus a variable number of bullets, capped at **6** — not a fixed count. A quiet month should not manufacture bullets to hit a target; a rough month should not be truncated below what's actually flagged.

**Architecture**: a new backend endpoint, separate from `POST /api/vdt/variance-analysis` since the prompt shape is fundamentally different (a monthly-series walk over flagged nodes, not a two-point diff over a full subtree) — reuses ADR-0034's model choice (`gpt-4o-mini`, `temperature=0.3`) since payload complexity is comparable once bounded to flagged nodes, and its in-memory caching pattern.

**Cache/reset behavior**: cached per `(company, year, scenario)`; a Company, Year, or Actual/Budget change invalidates the cached result the same way VDT Variance Analysis resets its narrative on scope/period changes (ADR-0034). The GL-code toggle, Monetary display scale, and YTD toggle do not invalidate it — none of them change the underlying monthly data Trend Analysis reads.

## Considered and rejected

**Reusing Variance Analysis's endpoint/prompt as-is** (treating Trends as "compare January to December"): rejected — collapses 12 months to a single two-point diff, discarding exactly the month-by-month trend shape this feature exists to surface, and loses any mid-year anomaly that both nets out by December.

**Letting the LLM detect anomalies itself from the raw 12-month tree**: rejected — same rationale as ADR-0034's arithmetic principle; asking the LLM to both discover *what's* material and explain it risks inconsistent or hallucinated significance judgments where a deterministic threshold is straightforward to compute server-side.

**Disabling the Budget chip for Trend Analysis** (Actual-only, mirroring the table's current dash-for-Budget state): rejected once it was clear `DriverFact` already carries a scenario dimension seeded for Budget — the correct fix is wiring `monthlyBudget` through the same engine call already producing `monthlyActual`, not special-casing the narrative around a gap that's cheap to close.

**A fixed bullet count (e.g. always 4, matching Variance Analysis)**: rejected — Variance Analysis's fixed range fits a single delta with a handful of contributors; a whole-year, whole-tree scan can legitimately surface anywhere from 2 to several flagged items depending on how eventful the year was, and forcing a fixed count would either pad quiet months or truncate rough ones.

## Open items

`monthlyBudget` wiring lands as part of this feature's backend work, not as separately-scheduled follow-up (unlike ADR-0039, which deferred it entirely). Multi-company aggregation is out of scope — VDT Trends uses the same fixed single-company pilot scope as VDT Variance Analysis and Reconciliation, so Trend Analysis inherits that constraint rather than introducing new scope-selection behavior.

**Status**: accepted
