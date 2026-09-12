"""VDT Sensitivity Analysis — elasticity ranking of terminal Drivers against
NPAT by perturbation — see docs/adr/0043.

Mirrors variance_analysis.py/trend_analysis.py's shape (on-demand analytic
module, no persistence, no caching — see the ADR's "Compute trigger"
decision), but holds no LLM narrative code: v1 is chart+table only. Endpoint
wiring (request validation, SSE framing) stays in main.py, matching every
other analysis module in this codebase.

Deviation from spec.md §1.1's literal `engine.target_value(root_code,
scenario)` wording: NPAT (a GL Reporting Root) is never itself a
`DriverFormula` target — only VDT Accounts and Drivers are — so
`DriverEngine.target_value()` called directly on the root always returns an
all-zero series (verified empirically against the test fixture). The ADR's
own "Compute method" decision is unambiguous on this point ("re-run
DriverEngine up through vdt_tree to NPAT"), so `compute_npat_with_overrides`
overlays facts onto a fresh engine and then runs `vdt_tree.build_vdt_tree()`
(now accepting that pre-built engine, see vdt_tree.py) to get NPAT's real,
whole-tree-rolled-up value — the spec bullet is read as shorthand for that
pipeline, not a literal call.
"""

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import Iterator, Optional

from sqlmodel import Session

from driver_engine import DriverEngine
from models import FormulaOperator
from vdt_tree import build_vdt_tree

ZERO = Decimal("0")

# Both relative, not fixed — a legitimately small-but-nonzero series isn't
# wrongly flagged, while a genuinely all-zero/sign-cancelling window is
# caught regardless of unit magnitude (see spec.md RESOLVED DECISIONS #2).
NPAT_REL_EPSILON = Decimal("0.005")
DRIVER_REL_EPSILON = Decimal("0.005")

# Upfront cap on total engine reruns (terminal Drivers in scope x 2
# directions). A rerun batches every month in the window into ONE
# compute_npat_with_overrides() call (one build_vdt_tree() walk covering
# the whole DriverOverride.monthly_values array) rather than one walk per
# month, so window width no longer multiplies the cycle count — only
# amortized cost-per-call scales with it. An unbounded whole-book run is
# still real compute cost multiplied by however many concurrent SSE
# connections are open (see docs/adr/0043's "Open items"); this cap
# remains deliberately conservative for a browser-facing on-demand run.
SENSITIVITY_MAX_CYCLES = 1500


@dataclass
class DriverOverride:
    driver_code: str
    monthly_values: list[Decimal]  # len == len(month_codes), ordered same as month_codes


def compute_npat_with_overrides(
    session: Session,
    company: str,
    source: str,
    month_codes: list[str],
    overrides: list[DriverOverride],
    target_code: str,
    include_subtree: bool = False,
) -> dict:
    """Construct a FRESH `DriverEngine` on EVERY call, overlay `overrides`
    in memory onto its `facts`, and recompute `target_code`'s monthly value
    for `month_codes` — see docs/adr/0043's "API shape" decision.

    Isolation guarantee: the engine is per-call and the overlay touches only
    that engine's own `facts` dict — never `session.add`, never `DriverFact`,
    never a commit. Two directions of one run, two concurrent requests, or
    two browser tabs never share an engine or a `_cache` entry. Uses the
    passed-in `session` (not `db.engine` directly) so test_main.py's
    `dependency_overrides[get_session]` in-memory DB is honoured.

    `subtree` stays `None` unless `include_subtree=True` — v1 Sensitivity
    Analysis only needs `npat`; the param exists so a future Simulation
    caller can ask for the full recomputed tree without a signature change.
    """
    engine = DriverEngine(session, [company], month_codes)
    for override in overrides:
        # `facts` is a defaultdict — a driver with no baseline fact still
        # overlays cleanly, no pre-seeding required.
        engine.facts[override.driver_code][company][source] = list(override.monthly_values)

    nodes = build_vdt_tree(session, [company], month_codes=month_codes, engine=engine)
    entry = nodes.get(target_code)
    field = "monthlyActual" if source == "actual" else "monthlyBudget"
    npat = [Decimal(str(v)) for v in entry[field]] if entry is not None else [ZERO] * len(month_codes)
    return {"npat": npat, "subtree": nodes if include_subtree else None}


def terminal_driver_candidates(engine: DriverEngine, scope_node_code: str, vdt_nodes: dict) -> list[str]:
    """Sorted unique terminal (`DriverFact`-backed) Driver codes reachable
    from `scope_node_code`'s VDT subtree — the candidate ROWS for a
    Sensitivity run (see docs/adr/0043's "Target is always NPAT" decision:
    scope only filters which Drivers get tested, never truncates what a
    shown Driver's elasticity means, since it's always measured to NPAT).

    Step A walks the already-built `vdt_nodes` tree (own `visited` set,
    cycle-safe though the tree is acyclic) to collect the scope's descendant
    codes. Step B recurses the FORMULA graph from each driven code collected
    there, guarded by a `visiting` frozenset — independent of
    `DriverCycleError` (which only fires during evaluation), so a cyclic
    formula graph can't hang this upfront walk.
    """
    scope_codes: set[str] = set()

    def collect_scope_codes(code: str) -> None:
        if code in scope_codes:
            return
        scope_codes.add(code)
        node = vdt_nodes.get(code)
        if node is None:
            return
        for child_id in node.get("childIds", []):
            collect_scope_codes(child_id)

    collect_scope_codes(scope_node_code)

    def collect_terminals(target_code: str, visiting: frozenset) -> set[str]:
        if target_code in visiting:
            return set()  # cycle guard — bail, do NOT recurse
        if target_code in engine.driver_by_code and not engine.is_driven(target_code):
            return {target_code}  # terminal Driver
        out: set[str] = set()
        for formula in engine.formulas_for(target_code):
            for term in engine.terms_by_formula.get(formula.code, []):
                out |= collect_terminals(term.driver_code, visiting | {target_code})
        return out

    terminals: set[str] = set()
    for code in scope_codes:
        if engine.is_driven(code):
            terminals |= collect_terminals(code, frozenset())

    return sorted(terminals)


@dataclass
class DirectionResult:
    elasticity_pct: Optional[float]  # %DeltaNPAT / %Deltadriver ; None when N/A
    npat_impact: float  # Sigma(bumped NPAT - baseline NPAT) over window, signed
    polarity: str  # 'favourable' | 'adverse' | 'neutral'

    def to_dict(self) -> dict:
        return {"elasticityPct": self.elasticity_pct, "npatImpact": self.npat_impact, "polarity": self.polarity}


@dataclass
class CandidateResult:
    driver_code: str
    description: str
    unit: str  # OperationalUnit value
    up: DirectionResult
    down: DirectionResult
    rank_magnitude: Optional[float]
    na: bool
    na_reason: Optional[str]  # 'baseline-driver-zero' | 'divide-by-zero' | 'baseline-npat-zero'

    def to_dict(self) -> dict:
        return {
            "driverCode": self.driver_code,
            "description": self.description,
            "unit": self.unit,
            "up": self.up.to_dict(),
            "down": self.down.to_dict(),
            "rankMagnitude": self.rank_magnitude,
            "na": self.na,
            "naReason": self.na_reason,
        }


def _is_near_zero(values: list[Decimal], rel_epsilon: Decimal) -> bool:
    """A series is "near zero" for the window when its sum's magnitude is
    small relative to its own average absolute monthly magnitude — see
    spec.md RESOLVED DECISIONS #2. An all-zero series has no magnitude to be
    relative to, so it's near-zero by definition (a bare `sum < eps * avg`
    test would otherwise read `0 < eps * 0` as False and miss it)."""
    if not values:
        return True
    avg_abs = sum((abs(v) for v in values), ZERO) / len(values)
    if avg_abs == ZERO:
        return True
    return abs(sum(values, ZERO)) < rel_epsilon * avg_abs


def _consumed_by_map(engine: DriverEngine) -> dict[str, set[str]]:
    """Reverse of `terms_by_formula`: which formula TARGETS consume a given
    driver code as a term operand — the "what does this driver's value feed
    into" edge the divide-by-zero preflight walks forward across (§1.3 step 4)."""
    consumed_by: dict[str, set[str]] = defaultdict(set)
    for formula in engine.formula_by_code.values():
        for term in engine.terms_by_formula.get(formula.code, []):
            consumed_by[term.driver_code].add(formula.target_code)
    return consumed_by


def _reachable_chain(start: str, consumed_by: dict[str, set[str]], visiting: frozenset = frozenset()) -> set[str]:
    if start in visiting:
        return set()
    result = {start}
    for nxt in consumed_by.get(start, ()):
        result |= _reachable_chain(nxt, consumed_by, visiting | {start})
    return result


def _zero_divisor_drivers(engine: DriverEngine, source: str) -> set[str]:
    """Driver codes that are EVER used as a DIVIDE operand's divisor whose
    own baseline monthly value hits exactly zero in some month — an exact
    per-month `== ZERO` check (not a relative one), since this is about the
    engine's `a / b if b else ZERO` masking hazard (driver_engine.py line
    129), not about magnitude. See §1.3 step 4's "conservative acceptable
    form": flags the driver itself, independent of which formula it's a
    divisor in — a candidate is tainted if the candidate OR anything on its
    reachable-to-NPAT chain is in this set (see `terminal_driver_candidates`'
    caller in `compute_sensitivity`)."""
    tainted: set[str] = set()
    for formula in engine.formula_by_code.values():
        for term in engine.terms_by_formula.get(formula.code, []):
            if term.operand_index == 0 or term.operator != FormulaOperator.DIVIDE:
                continue  # first operand seeds the running product/quotient — operator ignored there
            values = engine.driver_value(term.driver_code, source)
            if any(v == ZERO for v in values):
                tainted.add(term.driver_code)
    return tainted


def compute_sensitivity(
    session: Session,
    company: str,
    source: str,
    month_codes: list[str],
    root_code: str,
    candidates: list[str],
    bump_pct: float,
    engine: DriverEngine,
    total: int,
) -> Iterator[dict]:
    """Generator driving the whole elasticity run — see docs/adr/0043's
    "Progress reporting" decision. Yields `{"type": "progress", ...}` after
    EACH per-driver-direction rerun (all months in the window batched into
    one `compute_npat_with_overrides` call — see module docstring's
    `SENSITIVITY_MAX_CYCLES` note), `{"type": "candidate", "candidate": ...}`
    once a candidate's own result is final (both directions done, or
    immediately for a skip-compute N/A) so the frontend can render the
    tornado chart progressively rather than waiting for the whole run, and
    finally exactly one `{"type": "result", ...}` carrying the authoritative
    ranked/candidates lists (rank order isn't stable until every candidate's
    in, so the live progressive view is provisional — see docs/adr/0043).
    A plain (sync) generator so main.py's SSE loop can check
    `request.is_disconnected()` between `next()` calls and simply stop
    consuming it early — nothing further gets computed once the caller
    abandons the loop (generators are lazy).

    `engine` is the ONE baseline `DriverEngine` main.py already built for
    candidate discovery — reused here read-only for baseline driver values
    and the divide-by-zero preflight (§1.5: "reused read-only"). Every
    bumped rerun still goes through `compute_npat_with_overrides`, which
    always builds its OWN fresh engine (see that function's docstring) —
    `engine` here never touches a bumped computation.
    """
    bump_frac = Decimal(str(bump_pct)) / Decimal("100")

    baseline = compute_npat_with_overrides(session, company, source, month_codes, [], root_code)
    baseline_npat = baseline["npat"]
    baseline_sum = sum(baseline_npat, ZERO)
    npat_near_zero = _is_near_zero(baseline_npat, NPAT_REL_EPSILON)

    baseline_driver = {code: engine.driver_value(code, source) for code in candidates}

    zero_divisors = _zero_divisor_drivers(engine, source)
    consumed_by = _consumed_by_map(engine)
    divide_tainted = {code for code in candidates if _reachable_chain(code, consumed_by) & zero_divisors}

    candidate_results: list[CandidateResult] = []
    completed = 0

    for code in candidates:
        driver = engine.driver_by_code[code]

        # Priority order matches spec.md §1.3: a near-zero window NPAT
        # overrides every other reason uniformly (every candidate gets the
        # same reason, see §1.4), ahead of a per-candidate zero driver/
        # divide-by-zero taint.
        skip_compute = False
        if npat_near_zero:
            na, na_reason = True, "baseline-npat-zero"
        elif _is_near_zero(baseline_driver[code], DRIVER_REL_EPSILON):
            na, na_reason, skip_compute = True, "baseline-driver-zero", True
        elif code in divide_tainted:
            na, na_reason, skip_compute = True, "divide-by-zero", True
        else:
            na, na_reason = False, None

        if skip_compute:
            candidate_results.append(
                CandidateResult(
                    driver_code=code,
                    description=driver.description,
                    unit=driver.unit.value,
                    up=DirectionResult(None, 0.0, "neutral"),
                    down=DirectionResult(None, 0.0, "neutral"),
                    rank_magnitude=None,
                    na=True,
                    na_reason=na_reason,
                )
            )
            yield {"type": "candidate", "candidate": candidate_results[-1].to_dict()}
            continue

        # Baseline-NPAT-near-zero candidates still get bumped for real $
        # deltas (spec.md §1.3 step 3: "still return npat_impact deltas —
        # absolute $ stays meaningful"); only elasticity_pct is suppressed
        # below (dividing by a near-zero baseline is the undefined part).
        directions: dict[str, DirectionResult] = {}
        for key, sign in (("up", 1), ("down", -1)):
            # One call for the whole window, not one per month — build_vdt_tree()
            # and the DriverEngine it's fed already walk every month in a single
            # pass; looping compute_npat_with_overrides() per month was paying
            # for that walk M times over for no reason (see SENSITIVITY_MAX_CYCLES).
            bumped_values = [v * (Decimal("1") + sign * bump_frac) for v in baseline_driver[code]]
            rerun = compute_npat_with_overrides(
                session, company, source, month_codes, [DriverOverride(code, bumped_values)], root_code
            )
            bumped_sum = sum(rerun["npat"], ZERO)
            completed += 1
            yield {"type": "progress", "completed": completed, "total": total}

            npat_impact = bumped_sum - baseline_sum
            if na:
                elasticity_pct: Optional[Decimal] = None
            else:
                pct_npat = npat_impact / abs(baseline_sum)
                pct_driver = Decimal(str(sign)) * bump_frac
                elasticity_pct = (pct_npat / pct_driver) * Decimal("100")
            polarity = "favourable" if npat_impact > 0 else "adverse" if npat_impact < 0 else "neutral"
            directions[key] = DirectionResult(
                float(elasticity_pct) if elasticity_pct is not None else None, float(npat_impact), polarity
            )

        up, down = directions["up"], directions["down"]
        rank_magnitude = None if na else max(abs(up.elasticity_pct), abs(down.elasticity_pct))
        candidate_results.append(
            CandidateResult(
                driver_code=code,
                description=driver.description,
                unit=driver.unit.value,
                up=up,
                down=down,
                rank_magnitude=rank_magnitude,
                na=na,
                na_reason=na_reason,
            )
        )
        yield {"type": "candidate", "candidate": candidate_results[-1].to_dict()}

    ranked = sorted(
        (c for c in candidate_results if not c.na),
        key=lambda c: c.rank_magnitude if c.rank_magnitude is not None else -1.0,
        reverse=True,
    )[:10]

    if not candidates:
        reason: Optional[str] = "no-terminal-drivers"
    elif candidate_results and all(c.na for c in candidate_results):
        reason = "all-na"
    else:
        reason = None

    yield {
        "type": "result",
        "source": source,
        "months": month_codes,
        "baselineNpat": float(baseline_sum),
        "npatNearZero": npat_near_zero,
        "reason": reason,
        "candidateCount": len(candidates),
        "ranked": [c.to_dict() for c in ranked],
        "candidates": [c.to_dict() for c in candidate_results],
    }
