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

from diagnostic_content import DIAGNOSTIC_CONTENT
from driver_engine import DriverEngine
from models import GLFact, GLNode, NodeType, NormalBalance, Period, PeriodType
from periods import load_period_hierarchy, month_codes_of_year, month_indices_for, ytd_month_indices_for


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
            "monthlyPriorYear": [_money_json(v) if is_money else float(round(v, 3)) for v in prior_monthly],
            "direction": _direction(actual, budget),
            "hasFullData": False,
        }

    return nodes, formula_ids


# Node types whose "actual" is same-company-currency money, across both hierarchies
# (see docs/adr/0033) — Driver/Driver Formula units (rate/%/days/ratio)
# aren't, so favourable/adverse doesn't apply to them.
MONEY_NODE_TYPES = {
    NodeType.REPORTING_ROOT.value,
    NodeType.REPORTING_NODE.value,
    NodeType.POSTING_GL_ACCOUNT.value,
    "Activity Node",
    "Posting Activity Account",
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


def _year_of(period_by_code: dict[str, Period], code: str) -> str:
    """Walks up to the Year ancestor of `code` (or returns `code` itself if it already is one)."""
    node = period_by_code[code]
    while node.period_type != PeriodType.YEAR:
        node = period_by_code[node.parent_code]
    return node.code


def _prior_year_code(period_by_code: dict[str, Period], year_code: str) -> Optional[str]:
    order = period_by_code[year_code].order
    for code, p in period_by_code.items():
        if p.period_type == PeriodType.YEAR and p.order == order - 1:
            return code
    return None


def scoped_sum(monthly_values: list[Decimal], scope_indices: Optional[set[int]]) -> Decimal:
    if scope_indices is None:
        return sum(monthly_values, ZERO)
    return sum((monthly_values[i] for i in scope_indices), ZERO)


def load_monthly(
    session: Session,
    companies: list[str],
    period_by_code: dict[str, Period],
    period_children: dict[str, list[str]],
    target_year_code: Optional[str],
) -> dict[str, dict[str, list[Decimal]]]:
    """gl_code -> scenario -> 12-wide monthly array, scoped to one Year and
    `companies` — see docs/adr/0032 (facts across different fiscal years
    share month-array indices 0-11, so mixing years here would silently
    sum e.g. FY24-M01 and FY26-M01 into the same slot).
    """
    result: dict[str, dict[str, list[Decimal]]] = defaultdict(lambda: defaultdict(lambda: [ZERO] * 12))
    if not companies or target_year_code is None:
        return result
    month_codes = month_codes_of_year(period_by_code, period_children, target_year_code)
    # Selecting only the needed columns (rather than full GLFact rows)
    # skips ORM row hydration, the dominant cost for ~40k facts per scope.
    facts = session.exec(
        select(GLFact.code, GLFact.scenario, GLFact.period_code, GLFact.amount)
        .where(col(GLFact.company).in_(companies))
        .where(col(GLFact.period_code).in_(list(month_codes)))
    ).all()
    for code, scenario, fact_period_code, amount in facts:
        result[code][scenario.value][month_codes[fact_period_code]] += _decimal(amount)
    return result


def compute_gl_leaf(
    node: GLNode,
    engine: DriverEngine,
    monthly: dict[str, dict[str, list[Decimal]]],
    prior_monthly: dict[str, dict[str, list[Decimal]]],
    scope_indices: Optional[set[int]],
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
        scenarios = monthly.get(code, {})
        actual_monthly = scenarios.get("actual", [ZERO] * 12)
        budget_monthly = scenarios.get("budget", [ZERO] * 12)
    # Real prior-year comparison is just that year's own actuals, not
    # a separate stored scenario (see docs/adr/0032) — zero for the
    # earliest seeded year, where there's no year before it.
    prior_actual_monthly = prior_monthly.get(code, {}).get("actual", [ZERO] * 12)
    sign = 1 if node.normal_balance == NormalBalance.CREDIT else -1
    monthly_actual = [v * sign for v in actual_monthly]
    monthly_prior = [v * sign for v in prior_actual_monthly]
    return {
        "monthlyActual": monthly_actual,
        "monthlyPriorYear": monthly_prior,
        "actual": scoped_sum(monthly_actual, scope_indices),
        "budget": scoped_sum(budget_monthly, scope_indices) * sign,
        "priorYear": scoped_sum(monthly_prior, scope_indices),
    }


def sum_children_entry(child_entries: list[dict]) -> dict:
    """An internal (non-leaf) node's computed entry — the bottom-up sum of
    its children's entries. Shared by build_tree() (Reporting Node) and
    vdt_tree.py (Activity Node) — summing children is summing children
    regardless of which table the parent/children rows live in."""
    monthly_actual = [sum((e["monthlyActual"][i] for e in child_entries), ZERO) for i in range(12)]
    monthly_prior = [sum((e["monthlyPriorYear"][i] for e in child_entries), ZERO) for i in range(12)]
    return {
        "monthlyActual": monthly_actual,
        "monthlyPriorYear": monthly_prior,
        "actual": sum((e["actual"] for e in child_entries), ZERO),
        "budget": sum((e["budget"] for e in child_entries), ZERO),
        "priorYear": sum((e["priorYear"] for e in child_entries), ZERO),
    }


def build_tree(session: Session, companies: list[str], period_code: Optional[str] = None, ytd: bool = False) -> dict[str, dict]:
    nodes = session.exec(select(GLNode)).all()
    node_by_code = {n.code: n for n in nodes}
    children_by_parent: dict[str, list[str]] = defaultdict(list)
    for n in nodes:
        if n.parent_code:
            children_by_parent[n.parent_code].append(n.code)

    period_by_code, period_children = load_period_hierarchy(session)
    years = sorted((p for p in period_by_code.values() if p.period_type == PeriodType.YEAR), key=lambda p: p.order)
    # None means "the current/most recent year, in full" — multiple fiscal
    # years can coexist (see docs/adr/0032), so unlike a single-year dataset
    # this can no longer mean "sum every fact regardless of year".
    year_code = _year_of(period_by_code, period_code) if period_code is not None else (years[-1].code if years else None)
    prior_year_code = _prior_year_code(period_by_code, year_code) if year_code else None
    # None (whole year requested) means every one of the 12 monthly slots counts.
    scope_indices = (
        ytd_month_indices_for(period_by_code, period_children, period_code)
        if ytd
        else month_indices_for(period_by_code, period_children, period_code)
    )

    def scoped_sum_local(monthly_values: list[Decimal]) -> Decimal:
        return scoped_sum(monthly_values, scope_indices)

    monthly = load_monthly(session, companies, period_by_code, period_children, year_code)
    # A real prior-year comparison is just that year's own actuals, not a
    # separate stored scenario (see docs/adr/0032) — absent for the earliest
    # seeded year, where prior_monthly stays all-zero.
    prior_monthly = load_monthly(session, companies, period_by_code, period_children, prior_year_code)

    period_len = len(scope_indices) if scope_indices is not None else 12
    engine = DriverEngine(session, companies, year_code)

    computed: dict[str, dict] = {}

    def compute(code: str) -> dict:
        if code in computed:
            return computed[code]
        node = node_by_code[code]

        if node.node_type == NodeType.POSTING_GL_ACCOUNT:
            entry = compute_gl_leaf(node, engine, monthly, prior_monthly, scope_indices)
        else:
            child_entries = [compute(c) for c in children_by_parent.get(code, [])]
            entry = sum_children_entry(child_entries)

        computed[code] = entry
        return entry

    for code, node in node_by_code.items():
        if node.node_type == NodeType.REPORTING_ROOT:
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
            "nodeType": node.node_type.value,
            "unit": "money",
            "actual": _money_json(entry["actual"]),
            "budget": _money_json(entry["budget"]),
            "priorYear": _money_json(entry["priorYear"]),
            "monthlyActual": [_money_json(v) for v in entry["monthlyActual"]],
            "monthlyPriorYear": [_money_json(v) for v in entry["monthlyPriorYear"]],
            "direction": _direction(entry["actual"], entry["budget"]),
            "hasFullData": full_data is not None,
            **(full_data or {}),
        }

        if node.node_type == NodeType.POSTING_GL_ACCOUNT and engine.is_driven(code):
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
