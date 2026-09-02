"""Server-side rollup of the GL/FSI hierarchy for a requested scope.

A "scope" is a Company, Business Unit, or MISC Group code, resolved against
the company_node master data by company_tree.resolve_scope (see docs/adr/0028).
This module takes that resolved set of sampled companies and sums leaf fact
amounts bottom-up through the GL hierarchy (leaf magnitudes are always
positive in gl_fact; normal_balance flips the sign once, here, per
docs/adr/0023), returning a flat node map shaped like the frontend's existing
VdtNode contract.
"""

from collections import defaultdict
from typing import Optional

from sqlmodel import Session, col, select

from diagnostic_content import DIAGNOSTIC_CONTENT
from driver_engine import DriverEngine
from models import GLFact, GLNode, NodeType, NormalBalance
from periods import load_period_hierarchy, month_indices_for


def _direction(actual: float, budget: float) -> str:
    variance = actual - budget
    if abs(variance) < 1e-9:
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
            unit = "RM_M"
            actual, budget, prior = scoped_sum(actual_monthly), scoped_sum(budget_monthly), scoped_sum(prior_monthly)
        else:
            unit = engine.driver_by_code[owner_code].unit.value
            actual = scoped_sum(actual_monthly) / period_len
            budget = scoped_sum(budget_monthly) / period_len
            prior = scoped_sum(prior_monthly) / period_len

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
            d_actual = scoped_sum(d_actual_monthly) / period_len
            d_budget = scoped_sum(d_budget_monthly) / period_len
            d_prior = scoped_sum(d_prior_monthly) / period_len

            sub_nodes, sub_child_ids = _stitch_driver_nodes(engine, term.driver_code, occ_id, scoped_sum, period_len)

            nodes[occ_id] = {
                "id": occ_id,
                "name": driver.description,
                "parentId": f_id,
                "childIds": sub_child_ids,
                "nodeType": "Driver",
                "unit": driver.unit.value,
                "actual": round(d_actual, 3),
                "budget": round(d_budget, 3),
                "priorYear": round(d_prior, 3),
                "monthlyActual": [round(v, 3) for v in d_actual_monthly],
                "monthlyPriorYear": [round(v, 3) for v in d_prior_monthly],
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
            "actual": round(actual, 3),
            "budget": round(budget, 3),
            "priorYear": round(prior, 3),
            "monthlyActual": [round(v, 3) for v in actual_monthly],
            "monthlyPriorYear": [round(v, 3) for v in prior_monthly],
            "direction": _direction(actual, budget),
            "hasFullData": False,
        }

    return nodes, formula_ids


GL_NODE_TYPES = {NodeType.REPORTING_ROOT.value, NodeType.REPORTING_NODE.value, NodeType.POSTING_GL_ACCOUNT.value}


def diff_subtree(tree_a: dict[str, dict], tree_b: dict[str, dict], root: str) -> dict[str, dict]:
    """Diffs two build_tree() outputs (same companies, different periods) down
    from `root`, returning only that subtree with valueA/valueB/delta per
    node — see docs/adr/0031. `root`'s parentId is nulled so callers can walk
    the result exactly like a fresh tree (a root is whichever node has no
    parent). Driver/Driver Formula nodes get `direction: "neutral"` — their
    units aren't RM-comparable, so favourable/adverse doesn't apply to them.
    """
    result: dict[str, dict] = {}

    def walk(code: str) -> None:
        if code in result:
            return
        a, b = tree_a.get(code), tree_b.get(code)
        if a is None or b is None:
            return
        value_a, value_b = a["actual"], b["actual"]
        delta = round(value_b - value_a, 3)
        result[code] = {
            "id": code,
            "name": a["name"],
            "parentId": None if code == root else a["parentId"],
            "childIds": list(a["childIds"]),
            "nodeType": a["nodeType"],
            "unit": a["unit"],
            "valueA": round(value_a, 3),
            "valueB": round(value_b, 3),
            "delta": delta,
            "deltaPct": round(delta / abs(value_a) * 100, 1) if value_a else None,
            "direction": _direction(value_b, value_a) if a["nodeType"] in GL_NODE_TYPES else "neutral",
        }
        for child_id in a["childIds"]:
            walk(child_id)

    walk(root)
    return result


def build_tree(session: Session, companies: list[str], period_code: Optional[str] = None) -> dict[str, dict]:
    nodes = session.exec(select(GLNode)).all()
    node_by_code = {n.code: n for n in nodes}
    children_by_parent: dict[str, list[str]] = defaultdict(list)
    for n in nodes:
        if n.parent_code:
            children_by_parent[n.parent_code].append(n.code)

    period_by_code, period_children = load_period_hierarchy(session)
    # None means "the whole year" — every one of the 12 monthly slots counts.
    scope_indices = month_indices_for(period_by_code, period_children, period_code)

    def scoped_sum(monthly_values: list[float]) -> float:
        if scope_indices is None:
            return sum(monthly_values)
        return sum(monthly_values[i] for i in scope_indices)

    monthly: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(lambda: [0.0] * 12))
    if companies:
        # Selecting only the needed columns (rather than full GLFact rows)
        # skips ORM row hydration, the dominant cost for ~40k facts per scope.
        facts = session.exec(
            select(GLFact.code, GLFact.scenario, GLFact.period_code, GLFact.amount).where(col(GLFact.company).in_(companies))
        ).all()
        for code, scenario, fact_period_code, amount in facts:
            month_index = period_by_code[fact_period_code].order - 1
            monthly[code][scenario.value][month_index] += amount

    period_len = len(scope_indices) if scope_indices is not None else 12
    engine = DriverEngine(session, companies)

    computed: dict[str, dict] = {}

    def compute(code: str) -> dict:
        if code in computed:
            return computed[code]
        node = node_by_code[code]

        if node.node_type == NodeType.POSTING_GL_ACCOUNT:
            if engine.is_driven(code):
                # A Driver Formula bound to this leaf replaces its fabricated
                # gl_fact rows entirely — see docs/adr/0030.
                actual_monthly = engine.target_value(code, "actual")
                budget_monthly = engine.target_value(code, "budget")
                prior_monthly = engine.target_value(code, "prior_year")
            else:
                scenarios = monthly.get(code, {})
                actual_monthly = scenarios.get("actual", [0.0] * 12)
                budget_monthly = scenarios.get("budget", [0.0] * 12)
                prior_monthly = scenarios.get("prior_year", [0.0] * 12)
            sign = 1 if node.normal_balance == NormalBalance.CREDIT else -1
            monthly_actual = [v * sign for v in actual_monthly]
            monthly_prior = [v * sign for v in prior_monthly]
            entry = {
                "monthlyActual": monthly_actual,
                "monthlyPriorYear": monthly_prior,
                "actual": scoped_sum(monthly_actual),
                "budget": scoped_sum(budget_monthly) * sign,
                "priorYear": scoped_sum(monthly_prior),
            }
        else:
            child_entries = [compute(c) for c in children_by_parent.get(code, [])]
            monthly_actual = [sum(e["monthlyActual"][i] for e in child_entries) for i in range(12)]
            monthly_prior = [sum(e["monthlyPriorYear"][i] for e in child_entries) for i in range(12)]
            entry = {
                "monthlyActual": monthly_actual,
                "monthlyPriorYear": monthly_prior,
                "actual": sum(e["actual"] for e in child_entries),
                "budget": sum(e["budget"] for e in child_entries),
                "priorYear": sum(e["priorYear"] for e in child_entries),
            }

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
            "unit": "RM_M",
            "actual": round(entry["actual"], 3),
            "budget": round(entry["budget"], 3),
            "priorYear": round(entry["priorYear"], 3),
            "monthlyActual": [round(v, 3) for v in entry["monthlyActual"]],
            "monthlyPriorYear": [round(v, 3) for v in entry["monthlyPriorYear"]],
            "direction": _direction(entry["actual"], entry["budget"]),
            "hasFullData": full_data is not None,
            **(full_data or {}),
        }

        if node.node_type == NodeType.POSTING_GL_ACCOUNT and engine.is_driven(code):
            extra_nodes, formula_ids = _stitch_driver_nodes(engine, code, code, scoped_sum, period_len)
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
        d_actual = scoped_sum(d_actual_monthly) / period_len
        d_budget = scoped_sum(d_budget_monthly) / period_len
        d_prior = scoped_sum(d_prior_monthly) / period_len
        result[driver.code] = {
            "id": driver.code,
            "name": driver.description,
            "parentId": driver.displayed_under,
            "childIds": [],
            "nodeType": "Driver",
            "unit": driver.unit.value,
            "actual": round(d_actual, 3),
            "budget": round(d_budget, 3),
            "priorYear": round(d_prior, 3),
            "monthlyActual": [round(v, 3) for v in d_actual_monthly],
            "monthlyPriorYear": [round(v, 3) for v in d_prior_monthly],
            "direction": _direction(d_actual, d_budget),
            "hasFullData": False,
        }
        result[driver.displayed_under]["childIds"] = result[driver.displayed_under]["childIds"] + [driver.code]

    return result
