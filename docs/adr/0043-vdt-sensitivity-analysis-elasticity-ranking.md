# VDT Sensitivity Analysis ranks Drivers by NPAT elasticity

Zeteo's Driver Formula model (ADR-0030) lets any Driver Formula be decomposed into its terms, but nothing today tells the user *which* of those terms actually matters — which Driver, if it moved, would move NPAT the most. This is the first step toward a "what's the optimal price/level for this Driver" simulation capability, but that full capability (modelling a behavioural relationship between two Drivers, e.g. price ↔ volume, and sweeping for an optimum) requires an elasticity-curve data model that doesn't exist yet. This ADR scopes a narrower, immediately buildable precursor: rank a company's terminal Drivers by their **structural** impact on NPAT, using the formula tree as it already exists — no new schema, no behavioural modelling between Drivers.

## Decision

**Name**: "VDT Sensitivity Analysis" — joins VDT Trends / VDT Variance Analysis / Reconciliation as a fourth screen under the Value Driver nav dropdown, at `/vdt/sensitivity`.

**Scope of this ADR**: structural elasticity ranking only. Modelling an explicit behavioural relationship between two Drivers (e.g. a price Driver's effect on a volume Driver) so a true NPAT-maximizing point can be found — the Telco "optimal price" case that motivated this feature — is out of scope here and deferred to the future Simulation feature.

**Impact metric**: elasticity (%Δdriver → %Δtarget), not raw dollar impact. Drivers carry incompatible units (headcount, currency-per-month, ratio); a %→% metric ranks them on one comparable scale the way a raw-dollar bump could not.

**Compute method**: perturbation (bump-and-rerun), not closed-form calculus. Override one terminal Driver's `DriverFact` value, re-run `DriverEngine` up through `vdt_tree` to NPAT, diff against baseline. This is black-box with respect to formula shape (survives future formula-schema changes without re-deriving elasticity math) and — deliberately — is the same override mechanism the future Simulation feature will need for multi-Driver what-if runs.

**Bump size and direction**: user-configurable bump percentage, tested in both `+X%` and `-X%` directions. (Under the current pure-product/quotient formula model, with no caps or floors on `DriverFact` values, elasticity is mathematically symmetric — testing both directions is for UI legibility and to guard against future floor/cap logic, not because the math requires it.)

**Baseline period**: a period aggregate — Financial Year or Trailing window (same picker VDT Trends uses, see ADR-0042 Trailing window) — not a single-month snapshot. The bump is applied and NPAT re-derived for every month in the window; per-Driver deltas are summed across the window. Single company only, no cross-company consolidation (matches VDT Trends/Variance Analysis/Reconciliation's existing single-company pilot scope).

**Target is always NPAT**: every tested Driver's impact is measured all the way through to NPAT (global impact), not to its immediate formula parent (local impact). The user instead picks a **scope** — a VDT node (Activity Node, GL leaf, or the whole book) — that determines which terminal Drivers underneath it get tested, defaulting to the whole book (NPAT root) on first load. Only terminal (`DriverFact`-backed) Drivers are perturbation candidates; composite Drivers computed by their own Driver Formula aren't directly bumped, since they have no stored value to override.

**Ranking and display**: top 10 Drivers by absolute elasticity, tornado chart plus a data table (Driver, elasticity %, $ impact both directions, unit/formula-target metadata). Tornado bars are coloured favourable/adverse by polarity, reusing the convention Comparison's profit-bridge waterfall already established (ADR-0031) rather than inventing a new one.

**No LLM narrative in v1**: chart and table only. The novelty here is the ranking itself; narrative can follow once the ranking's been validated against real data, the same staged approach ADR-0034 and ADR-0040 took before adding their LLM layer.

**Compute trigger**: on-demand (button-triggered), no caching — matches Variance Analysis (ADR-0034), not Trend Analysis's cache. The bump percentage is a free user input, which would fragment a cache key too fine to be useful.

**API shape**: a generic override primitive — given a list of `{driver_code, override_value}`, recompute and return NPAT (and subtree). Sensitivity Analysis's backend endpoint loops over this primitive internally (one call per terminal Driver per direction per month in the window) and streams progress rather than requiring the browser to issue one request per Driver. The primitive itself is the literal foundation the future Simulation feature reuses for multi-Driver overrides — Simulation doesn't need new backend plumbing, only a new endpoint (or none) composing the same primitive differently.

**Progress reporting**: total cycle count (terminal Drivers in scope × 2 directions × months in window) is cheap to compute upfront via a tree walk, before any `DriverEngine` reruns start — so a meaningful "N of M" progress bar is buildable. Delivered via Server-Sent Events: the backend pushes a progress event after each engine rerun and closes with a final result event carrying the ranked list. This is the first streaming-response endpoint in this codebase; the frontend reads it via `fetch()` + manual `ReadableStream` consumption rather than the native `EventSource` API, since `EventSource` doesn't support POST bodies and this endpoint needs one (scope, period, bump%, direction set). The backend checks `request.is_disconnected()` between reruns and stops early if the client has gone away, so an abandoned whole-book request doesn't keep consuming compute for no one.

## Considered and rejected

**Behavioural/elasticity-curve modelling now** (true price↔volume optimal-point simulation, the literal Telco example): rejected for this ADR — it requires a new data model (explicit relationships between Driver pairs) that doesn't exist, and conflating it with the structural ranking here would block shipping either. Becomes its own future ADR once the ranking has proven out which Drivers are worth modelling a curve for.

**Analytical/closed-form elasticity** (derive each Driver's elasticity from its term's $ value share of the target, no engine rerun): rejected in favour of perturbation — faster and exact today, but the derivation is tied to the current flat sum-of-products formula shape and would need re-deriving if that schema changes (see the divide-by-sum discussion that predates this ADR). Perturbation is also the mechanism Simulation needs regardless, so building it once here avoids building it twice.

**Fixed 1% bump size**: rejected in favour of user-configurable, even though the current formula model makes elasticity bump-size-invariant — configurability was chosen for UI flexibility (e.g. testing a specific "what if this moved 5%" question) even in this precursor phase.

**Single bump direction only**: rejected — despite the model being symmetric today, showing both directions reads more intuitively ("if this driver rose vs fell") and doesn't assume away future floor/cap logic on `DriverFact`.

**Purpose-built ranking endpoint instead of a generic override primitive**: rejected — a single endpoint that internally loops and returns a ranked list is simpler for this feature alone, but would leave Simulation needing its own, separate multi-override endpoint later, with the two code paths free to drift apart. Building the primitive first costs little extra now and removes that duplication risk.

**Polling job endpoint for progress** (`POST /start` returns a job id, `GET /status/{id}` polled every ~500ms): rejected in favour of SSE — polling needs an in-memory job registry (lifecycle, TTL eviction for abandoned jobs) that doesn't exist anywhere in this codebase; SSE needs no job storage, just a held-open connection, at the cost of being this codebase's first streaming-response pattern.

**Precomputed/cached results** (Trend Analysis's pattern): rejected — the user-configurable bump% makes the cache key too fine-grained to usefully hit, and on-demand keeps this consistent with Variance Analysis's isolated, never-auto-fired behaviour.

**LLM-narrated top Drivers** (Variance/Trend Analysis's pattern): rejected for v1 — the ranking itself is the new capability being validated; narrative is additive scope better added once real data has exercised the ranking.

## Open items

Whole-book default scope combined with a period-aggregate baseline could mean dozens of `DriverEngine` reruns on first load (K Drivers × 2 directions × M months) — the SSE progress bar exists specifically to make that latency legible, not to eliminate it. If real data proves this too slow even with progress feedback, the default scope or baseline window may need revisiting.

Elasticity is undefined (division by zero) when a Driver's baseline value, or a term's baseline value, is zero. Needs explicit handling (excluded from ranking / flagged N/A) rather than left to crash or produce `Infinity` — left to implementation to resolve cleanly.

Two existing ADR files are both numbered 0042 (`0042-vdt-trends-trailing-window.md` and `0042-vdt-variance-same-grain-period-comparison.md`) — a pre-existing collision, unrelated to this feature. This ADR takes the next free number, 0043.

**Status**: accepted
