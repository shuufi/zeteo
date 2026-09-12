"""Server-side rollup of the GL/FSI hierarchy for a requested scope.

A monetary "scope" is one Company code, resolved against the company_node
master data by company_tree.resolve_scope (see docs/adr/0028 and 0035).
This module takes that resolved sampled company and sums leaf fact
amounts bottom-up through the GL hierarchy (leaf magnitudes are always
positive in gl_fact; normal_balance flips the sign once, here, per
docs/adr/0023), returning a flat node map shaped like the frontend's existing
VdtNode contract.
"""

from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

from sqlmodel import Session, col, select

from backend.diagnostics.content import DIAGNOSTIC_CONTENT
from backend.drivers.engine import DriverEngine
from backend.accounting.models import Financial, GLAccount, GLHierarchy, NormalBalance
from backend.calendar.periods import load_years, month_indices_for, ytd_month_indices_for


ZERO = Decimal("0")
MONEY_QUANTUM = Decimal("0.01")


def _decimal(value: Decimal | float | int) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _money_json(value: Decimal | float | int) -> float:
    return float(_decimal(value).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP))


def _direction(actual: Decimal | float, budget: Decimal | float) -> str:
    variance = _decimal(actual) - _decimal(budget)
    if abs(variance) < Decimal("0.000000001"):
        return "neutral"
    return "favourable" if variance > 0 else "adverse"


def _stitch_driver_nodes(
    engine: DriverEngine,
    owner_code: str,
    owner_id: str,
    scoped_sum,
    period_len: int,
) -> tuple[dict[str, dict], list[str]]:
    """Attach Driver Formula / Driver nodes below `owner_code` (a GL leaf or
    Driver raw code, whose already-resolved tree id is `owner_id`).

    Recurses into a Driver's own bound Formulas where present (see
    docs/adr/0030) — ids are scoped by the full ancestor path so the same
    Driver reused under a different Formula gets its own tree position
    without id collisions (tree position is a view artifact; the underlying
    value, via `engine`, is computed once and shared).
    """
    nodes: dict[str, dict] = {}
    formula_ids: list[str] = []
    is_money = owner_code not in engine.driver_by_code

    for formula in engine.formulas_for(owner_code):
        f_id = f"{owner_id}::{formula.code}"
        formula_ids.append(f_id)

        actual_monthly = engine.formula_value(formula, "actual", average=not is_money)
        budget_monthly = engine.formula_value(formula, "budget", average=not is_money)
        prior_monthly = engine.formula_value(formula, "prior_year", average=not is_money)

        if is_money:
            unit = "money"
            actual, budget, prior = scoped_sum(actual_monthly), scoped_sum(budget_monthly), scoped_sum(prior_monthly)
        else:
            unit = engine.driver_by_code[owner_code].unit.value
            divisor = Decimal(period_len)
            actual = scoped_sum(actual_monthly) / divisor
            budget = scoped_sum(budget_monthly) / divisor
            prior = scoped_sum(prior_monthly) / divisor

        term_child_ids: list[str] = []
        seen_drivers: list[str] = []
        for term in engine.terms_by_formula.get(formula.code, []):
            if term.driver_code in seen_drivers:
                continue
            seen_drivers.append(term.driver_code)
            driver = engine.driver_by_code[term.driver_code]
            occ_id = f"{f_id}::{term.driver_code}"
            term_child_ids.append(occ_id)

            d_actual_monthly = engine.driver_value(term.driver_code, "actual")
            d_budget_monthly = engine.driver_value(term.driver_code, "budget")
            d_prior_monthly = engine.driver_value(term.driver_code, "prior_year")
            divisor = Decimal(period_len)
            d_actual = scoped_sum(d_actual_monthly) / divisor
            d_budget = scoped_sum(d_budget_monthly) / divisor
            d_prior = scoped_sum(d_prior_monthly) / divisor

            sub_nodes, sub_child_ids = _stitch_driver_nodes(engine, term.driver_code, occ_id, scoped_sum, period_len)

            nodes[occ_id] = {
                "id": occ_id,
                "name": driver.description,
                "parentId": f_id,
                "childIds": sub_child_ids,
                "nodeType": "Driver",
                "unit": driver.unit.value,
                "actual": float(round(d_actual, 3)),
                "budget": float(round(d_budget, 3)),
                "priorYear": float(round(d_prior, 3)),
                "monthlyActual": [float(round(v, 3)) for v in d_actual_monthly],
                "monthlyBudget": [float(round(v, 3)) for v in d_budget_monthly],
                "monthlyPriorYear": [float(round(v, 3)) for v in d_prior_monthly],
                "direction": _direction(d_actual, d_budget),
                "hasFullData": False,
            }
            nodes.update(sub_nodes)

        nodes[f_id] = {
            "id": f_id,
            "name": formula.description,
            "expression": engine.expression_text(formula.code),
            "parentId": owner_id,
            "childIds": term_child_ids,
            "nodeType": "Driver Formula",
            "unit": unit,
            "actual": _money_json(actual) if is_money else float(round(actual, 3)),
            "budget": _money_json(budget) if is_money else float(round(budget, 3)),
            "priorYear": _money_json(prior) if is_money else float(round(prior, 3)),
            "monthlyActual": [_money_json(v) if is_money else float(round(v, 3)) for v in actual_monthly],
            "monthlyBudget": [_money_json(v) if is_money else float(round(v, 3)) for v in budget_monthly],
            "monthlyPriorYear": [_money_json(v) if is_money else float(round(v, 3)) for v in prior_monthly],
            "direction": _direction(actual, budget),
            "hasFullData": False,
        }

    return nodes, formula_ids


# Node types whose "actual" is same-company-currency money, across both hierarchies
# (see docs/adr/0033) — Driver/Driver Formula units (rate/%/days/ratio)
# aren't, so favourable/adverse doesn't apply to them. GL's three values are
# derived strings now (see docs/adr/0048), not a stored NodeType enum, but
# the same three values still apply here.
MONEY_NODE_TYPES = {
    "Reporting Root",
    "Reporting Node",
    "Posting GL Account",
    "VDT Hierarchy Node",
    "VDT Account",
}


def diff_subtree(tree_a: dict[str, dict], tree_b: dict[str, dict], root: str) -> dict[str, dict]:
    """Diffs two build_tree()/build_vdt_tree() outputs (same companies,
    different periods) down from `root`, returning only that subtree with
    valueA/valueB/delta per node — see docs/adr/0031 and docs/adr/0034.
    `root`'s parentId is nulled so callers can walk the result exactly like a
    fresh tree (a root is whichever node has no parent). Driver/Driver
    Formula nodes get `direction: "neutral"` — their units aren't necessarily
    monetary, so favourable/adverse doesn't apply to them.
    """
    result: dict[str, dict] = {}

    def walk(code: str) -> None:
        if code in result:
            return
        a, b = tree_a.get(code), tree_b.get(code)
        if a is None or b is None:
            return
        value_a, value_b = _decimal(a["actual"]), _decimal(b["actual"])
        delta = value_b - value_a
        result[code] = {
            "id": code,
            "name": a["name"],
            "parentId": None if code == root else a["parentId"],
            "childIds": list(a["childIds"]),
            "nodeType": a["nodeType"],
            "unit": a["unit"],
            "valueA": _money_json(value_a),
            "valueB": _money_json(value_b),
            "delta": _money_json(delta),
            "deltaPct": float(round(delta / abs(value_a) * 100, 1)) if value_a else None,
            "direction": _direction(value_b, value_a) if a["nodeType"] in MONEY_NODE_TYPES else "neutral",
            **({"expression": a["expression"]} if "expression" in a else {}),
        }
        for child_id in a["childIds"]:
            walk(child_id)

    walk(root)
    return result


def subtree(tree: dict[str, dict], root: str) -> dict[str, dict]:
    """Slices one build_tree()/build_vdt_tree() output down to the subtree
    rooted at `root` — like diff_subtree() but for a single tree, no diffing
    (see docs/adr/0033's Reconciliation report, which shows two hierarchies'
    subtrees side by side rather than a delta). `root`'s parentId is nulled
    so callers can walk the result exactly like a fresh tree.
    """
    result: dict[str, dict] = {}

    def walk(code: str) -> None:
        if code in result:
            return
        node = tree.get(code)
        if node is None:
            return
        entry = dict(node)
        if code == root:
            entry["parentId"] = None
        result[code] = entry
        for child_id in node["childIds"]:
            walk(child_id)

    walk(root)
    return result


def periods_of_year(year: Optional[int]) -> Optional[list[tuple[int, int]]]:
    """One Year's 12 (year, month) pairs, chronological (Jan..Dec) order —
    shared by build_tree()/build_vdt_tree(), both of which need an explicit
    ordered window to restrict fact-loading to one fiscal year's months and
    avoid silently summing e.g. 2024's and 2026's period 1 into the same slot
    (see docs/adr/0032, docs/adr/0051)."""
    if year is None:
        return None
    return [(year, month) for month in range(1, 13)]


def scoped_sum(monthly_values: list[Decimal], scope_indices: Optional[set[int]]) -> Decimal:
    if scope_indices is None:
        return sum(monthly_values, ZERO)
    return sum((monthly_values[i] for i in scope_indices), ZERO)


def load_monthly(
    session: Session,
    companies: list[str],
    periods: Optional[list[tuple[int, int]]],
) -> dict[str, dict[str, list[Decimal]]]:
    """gl_code -> source -> monthly array (one slot per entry in `periods`,
    in that order) for `companies`. `periods` is an explicit, already-
    resolved ordered list of (year, month) pairs — a single Year's 12 months
    for build_tree()/build_vdt_tree()'s Financial Year path, or a Trailing-
    mode window that can span two fiscal years (see docs/adr/0032,
    docs/adr/0042, docs/adr/0051). Callers must never pass a `periods` that
    silently mixes two years into the same slot by coincidence — every caller
    here resolves its own explicit, deliberate window first.
    """
    width = len(periods) if periods else 12
    result: dict[str, dict[str, list[Decimal]]] = defaultdict(lambda: defaultdict(lambda: [ZERO] * width))
    if not companies or not periods:
        return result
    index_by_period = {period: i for i, period in enumerate(periods)}
    years = {year for year, _ in periods}
    # Selecting only the needed columns (rather than full Financial rows)
    # skips ORM row hydration, the dominant cost for ~40k facts per scope.
    facts = session.exec(
        select(Financial.code, Financial.source, Financial.year, Financial.period, Financial.amount)
        .where(col(Financial.company).in_(companies))
        .where(col(Financial.year).in_(years))
    ).all()
    for code, source, year, period, amount in facts:
        index = index_by_period.get((year, period))
        if index is None:
            continue
        result[code][source.value][index] += _decimal(amount)
    return result


def compute_gl_leaf(
    node: GLAccount,
    engine: DriverEngine,
    monthly: dict[str, dict[str, list[Decimal]]],
    prior_monthly: dict[str, dict[str, list[Decimal]]],
    scope_indices: Optional[set[int]],
    width: int = 12,
) -> dict:
    """A Posting GL Account leaf's computed entry — shared by build_tree() and
    vdt_tree.py's GL-passthrough branches (see docs/adr/0033)."""
    code = node.code
    if engine.is_driven(code):
        # A Driver Formula bound to this leaf replaces its fabricated
        # gl_fact rows entirely — see docs/adr/0030.
        actual_monthly = engine.target_value(code, "actual")
        budget_monthly = engine.target_value(code, "budget")
    else:
        sources = monthly.get(code, {})
        actual_monthly = sources.get("actual", [ZERO] * width)
        budget_monthly = sources.get("budget", [ZERO] * width)
    # Real prior-year comparison is just that year's own actuals, not
    # a separate stored source (see docs/adr/0032) — zero for the
    # earliest seeded year, where there's no year before it.
    prior_actual_monthly = prior_monthly.get(code, {}).get("actual", [ZERO] * width)
    sign = 1 if node.normal_balance == NormalBalance.CREDIT else -1
    monthly_actual = [v * sign for v in actual_monthly]
    monthly_budget = [v * sign for v in budget_monthly]
    monthly_prior = [v * sign for v in prior_actual_monthly]
    return {
        "monthlyActual": monthly_actual,
        "monthlyBudget": monthly_budget,
        "monthlyPriorYear": monthly_prior,
        "actual": scoped_sum(monthly_actual, scope_indices),
        "budget": scoped_sum(monthly_budget, scope_indices),
        "priorYear": scoped_sum(monthly_prior, scope_indices),
    }


def sum_children_entry(child_entries: list[dict], width: int = 12) -> dict:
    """An internal (non-leaf) node's computed entry — the bottom-up sum of
    its children's entries. Shared by build_tree() (Reporting Node) and
    vdt_tree.py (VDT Hierarchy Node) — summing children is summing children
    regardless of which table the parent/children rows live in. `width` must
    match the monthly-array width every child_entries member already carries
    (12 for Financial Year mode, the resolved window length for Trailing)."""
    monthly_actual = [sum((e["monthlyActual"][i] for e in child_entries), ZERO) for i in range(width)]
    monthly_budget = [sum((e["monthlyBudget"][i] for e in child_entries), ZERO) for i in range(width)]
    monthly_prior = [sum((e["monthlyPriorYear"][i] for e in child_entries), ZERO) for i in range(width)]
    return {
        "monthlyActual": monthly_actual,
        "monthlyBudget": monthly_budget,
        "monthlyPriorYear": monthly_prior,
        "actual": sum((e["actual"] for e in child_entries), ZERO),
        "budget": sum((e["budget"] for e in child_entries), ZERO),
        "priorYear": sum((e["priorYear"] for e in child_entries), ZERO),
    }


def _load_gl_hierarchy(
    session: Session,
) -> tuple[dict[str, GLHierarchy | GLAccount], dict[str, list[str]], set[str]]:
    """Loads both GLHierarchy (interior) and GLAccount (leaf) rows into one
    combined code-keyed map — see docs/adr/0048. `leaf_codes` is how callers
    tell the two apart, since neither table stores a node_type column.

    For a parent with both interior and leaf children (rare — 3 of 99 GL
    hierarchy nodes today), this always orders all interior children before
    all leaf children, since they're read from two separate tables/queries
    rather than one combined one. `financial-client.ts`'s `buildDisplayRows()`
    renders `childIds` in this exact order with no re-sort, so this does
    affect display order for a mixed parent — verified harmless against
    today's real seed data only because every mixed parent's leaf children
    already came after its interior children in the original CSV. No `order`
    column was added to preserve this byte-for-byte (see docs/adr/0048's
    rejection of `order`) since nothing today needs it; revisit if seed data
    ever puts a leaf before an interior sibling under the same parent."""
    hierarchy_nodes = session.exec(select(GLHierarchy)).all()
    accounts = session.exec(select(GLAccount)).all()
    node_by_code: dict[str, GLHierarchy | GLAccount] = {n.code: n for n in hierarchy_nodes}
    node_by_code.update({n.code: n for n in accounts})
    leaf_codes = {n.code for n in accounts}
    children_by_parent: dict[str, list[str]] = defaultdict(list)
    for n in hierarchy_nodes:
        if n.parent_code:
            children_by_parent[n.parent_code].append(n.code)
    for n in accounts:
        children_by_parent[n.parent_code].append(n.code)
    return node_by_code, children_by_parent, leaf_codes


def _node_type(code: str, node: GLHierarchy | GLAccount, leaf_codes: set[str]) -> str:
    """Derives the nodeType string the API contract (docs/adr/0044) still
    exposes, from table membership + parent_code — not a stored column, see
    docs/adr/0048. The Root/Node distinction is just "which row has no
    parent"; there is exactly one such row (NPAT)."""
    if code in leaf_codes:
        return "Posting GL Account"
    return "Reporting Root" if node.parent_code is None else "Reporting Node"


def _normal_balance(
    code: str,
    node_by_code: dict[str, GLHierarchy | GLAccount],
    children_by_parent: dict[str, list[str]],
    leaf_codes: set[str],
    cache: dict[str, Optional[NormalBalance]],
) -> Optional[NormalBalance]:
    """An interior node's balance is the union of its leaves' balances,
    `None` if mixed (e.g. Gross Profit) — computed here, not stored, since
    GLHierarchy carries no normal_balance column (docs/adr/0048)."""
    if code in cache:
        return cache[code]
    if code in leaf_codes:
        result = node_by_code[code].normal_balance
    else:
        balances = {_normal_balance(c, node_by_code, children_by_parent, leaf_codes, cache) for c in children_by_parent.get(code, [])}
        result = balances.pop() if len(balances) == 1 else None
    cache[code] = result
    return result


def build_gl_master_tree(session: Session) -> dict[str, dict]:
    """The raw GL/FSI chart-of-accounts hierarchy — master data, no financial
    figures (see docs/adr/0044). Mirrors build_company_tree()/build_period_tree()'s
    shape: a flat node map with `label` (not `name`, unlike build_tree()'s
    figure-bearing nodes), keyed by GL code.
    """
    node_by_code, children_by_parent, leaf_codes = _load_gl_hierarchy(session)
    balance_cache: dict[str, Optional[NormalBalance]] = {}
    result = {}
    for code, node in node_by_code.items():
        balance = _normal_balance(code, node_by_code, children_by_parent, leaf_codes, balance_cache)
        result[code] = {
            "id": code,
            "label": node.description,
            "parentId": node.parent_code,
            "childIds": list(children_by_parent.get(code, [])),
            "nodeType": _node_type(code, node, leaf_codes),
            "normalBalance": balance.value if balance else None,
        }
    return result


def build_tree(
    session: Session,
    companies: list[str],
    year: Optional[int] = None,
    quarter: Optional[int] = None,
    month: Optional[int] = None,
    ytd: bool = False,
) -> dict[str, dict]:
    node_by_code, children_by_parent, leaf_codes = _load_gl_hierarchy(session)

    years = load_years(session)
    # None means "the current/most recent year, in full" — multiple fiscal
    # years can coexist (see docs/adr/0032), so unlike a single-year dataset
    # this can no longer mean "sum every fact regardless of year".
    resolved_year = year if year is not None else (years[-1] if years else None)
    prior_year = resolved_year - 1 if resolved_year is not None and (resolved_year - 1) in years else None
    # None (whole year requested) means every one of the 12 monthly slots counts.
    scope_indices = ytd_month_indices_for(month, quarter) if ytd else month_indices_for(month, quarter)

    def scoped_sum_local(monthly_values: list[Decimal]) -> Decimal:
        return scoped_sum(monthly_values, scope_indices)

    periods = periods_of_year(resolved_year)
    prior_periods = periods_of_year(prior_year)
    width = len(periods) if periods else 12
    monthly = load_monthly(session, companies, periods)
    # A real prior-year comparison is just that year's own actuals, not a
    # separate stored source (see docs/adr/0032) — absent for the earliest
    # seeded year, where prior_monthly stays all-zero.
    prior_monthly = load_monthly(session, companies, prior_periods)

    period_len = len(scope_indices) if scope_indices is not None else width
    engine = DriverEngine(session, companies, periods)

    computed: dict[str, dict] = {}

    def compute(code: str) -> dict:
        if code in computed:
            return computed[code]
        node = node_by_code[code]

        if code in leaf_codes:
            entry = compute_gl_leaf(node, engine, monthly, prior_monthly, scope_indices, width)
        else:
            child_entries = [compute(c) for c in children_by_parent.get(code, [])]
            entry = sum_children_entry(child_entries, width)

        computed[code] = entry
        return entry

    for code, node in node_by_code.items():
        if code not in leaf_codes and node.parent_code is None:
            compute(code)

    result = {}
    for code, node in node_by_code.items():
        entry = computed[code]
        full_data = DIAGNOSTIC_CONTENT.get(code)
        result[code] = {
            "id": code,
            "name": node.description,
            "parentId": node.parent_code,
            "childIds": list(children_by_parent.get(code, [])),
            "nodeType": _node_type(code, node, leaf_codes),
            "unit": "money",
            "actual": _money_json(entry["actual"]),
            "budget": _money_json(entry["budget"]),
            "priorYear": _money_json(entry["priorYear"]),
            "monthlyActual": [_money_json(v) for v in entry["monthlyActual"]],
            "monthlyBudget": [_money_json(v) for v in entry["monthlyBudget"]],
            "monthlyPriorYear": [_money_json(v) for v in entry["monthlyPriorYear"]],
            "direction": _direction(entry["actual"], entry["budget"]),
            "hasFullData": full_data is not None,
            **(full_data or {}),
        }

        if code in leaf_codes and engine.is_driven(code):
            extra_nodes, formula_ids = _stitch_driver_nodes(engine, code, code, scoped_sum_local, period_len)
            result[code]["childIds"] = result[code]["childIds"] + formula_ids
            result.update(extra_nodes)

    # Legacy context-only Drivers (no Formula, driving nothing) keep rendering
    # under the GL leaf they historically explained via their display-only
    # anchor — see docs/adr/0030.
    for driver in engine.driver_by_code.values():
        if not driver.displayed_under or driver.displayed_under not in result or engine.is_driven(driver.code):
            continue
        d_actual_monthly = engine.driver_value(driver.code, "actual")
        d_budget_monthly = engine.driver_value(driver.code, "budget")
        d_prior_monthly = engine.driver_value(driver.code, "prior_year")
        divisor = Decimal(period_len)
        d_actual = scoped_sum_local(d_actual_monthly) / divisor
        d_budget = scoped_sum_local(d_budget_monthly) / divisor
        d_prior = scoped_sum_local(d_prior_monthly) / divisor
        result[driver.code] = {
            "id": driver.code,
            "name": driver.description,
            "parentId": driver.displayed_under,
            "childIds": [],
            "nodeType": "Driver",
            "unit": driver.unit.value,
            "actual": float(round(d_actual, 3)),
            "budget": float(round(d_budget, 3)),
            "priorYear": float(round(d_prior, 3)),
            "monthlyActual": [float(round(v, 3)) for v in d_actual_monthly],
            "monthlyPriorYear": [float(round(v, 3)) for v in d_prior_monthly],
            "direction": _direction(d_actual, d_budget),
            "hasFullData": False,
        }
        result[driver.displayed_under]["childIds"] = result[driver.displayed_under]["childIds"] + [driver.code]

    return result
