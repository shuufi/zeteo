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
from models import GLFact, GLNode, NodeType, NormalBalance
from periods import load_period_hierarchy, month_indices_for


def _direction(actual: float, budget: float) -> str:
    variance = actual - budget
    if abs(variance) < 1e-9:
        return "neutral"
    return "favourable" if variance > 0 else "adverse"


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

    computed: dict[str, dict] = {}

    def compute(code: str) -> dict:
        if code in computed:
            return computed[code]
        node = node_by_code[code]

        if node.node_type in (NodeType.POSTING_GL_ACCOUNT, NodeType.OPERATIONAL_DRIVER):
            scenarios = monthly.get(code, {})
            actual_monthly = scenarios.get("actual", [0.0] * 12)
            budget_monthly = scenarios.get("budget", [0.0] * 12)
            prior_monthly = scenarios.get("prior_year", [0.0] * 12)
            if node.node_type == NodeType.OPERATIONAL_DRIVER:
                # A rate/percent/day-count is meaningless summed across months
                # (see FinancialPerformance.svelte's own YTD-skip comment for
                # operational rows) — use the scoped-period average instead.
                period_len = len(scope_indices) if scope_indices is not None else 12
                entry = {
                    "monthlyActual": actual_monthly,
                    "monthlyPriorYear": prior_monthly,
                    "actual": scoped_sum(actual_monthly) / period_len,
                    "budget": scoped_sum(budget_monthly) / period_len,
                    "priorYear": scoped_sum(prior_monthly) / period_len,
                }
            else:
                sign = 1 if node.normal_balance == NormalBalance.CREDIT else -1
                monthly_actual = [v * sign for v in actual_monthly]
                monthly_prior = [v * sign for v in prior_monthly]
                entry = {
                    "monthlyActual": monthly_actual,
                    "monthlyPriorYear": monthly_prior,
                    "actual": scoped_sum(monthly_actual),
                    "budget": scoped_sum(budget_monthly) * sign,
                    "priorYear": scoped_sum(prior_monthly) * sign,
                }
        else:
            child_codes = [c for c in children_by_parent.get(code, []) if node_by_code[c].node_type != NodeType.OPERATIONAL_DRIVER]
            child_entries = [compute(c) for c in child_codes]
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
        if node.node_type in (NodeType.REPORTING_ROOT, NodeType.OPERATIONAL_DRIVER):
            compute(code)

    result = {}
    for code, node in node_by_code.items():
        entry = computed[code]
        full_data = DIAGNOSTIC_CONTENT.get(code)
        result[code] = {
            "id": code,
            "name": node.description,
            "parentId": node.parent_code,
            "childIds": children_by_parent.get(code, []),
            "nodeType": node.node_type.value,
            "unit": node.unit.value if node.unit else "RM_M",
            "actual": round(entry["actual"], 3),
            "budget": round(entry["budget"], 3),
            "priorYear": round(entry["priorYear"], 3),
            "monthlyActual": [round(v, 3) for v in entry["monthlyActual"]],
            "monthlyPriorYear": [round(v, 3) for v in entry["monthlyPriorYear"]],
            "direction": _direction(entry["actual"], entry["budget"]),
            "hasFullData": full_data is not None,
            **(full_data or {}),
        }
    return result
