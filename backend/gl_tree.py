"""Server-side rollup of the GL/FSI hierarchy for a requested scope.

A "scope" is either a sampled company code or a Business Unit code (see
docs/adr/0024). This module resolves a scope to its set of companies, sums
leaf fact amounts bottom-up through the hierarchy (leaf magnitudes are always
positive in gl_fact; normal_balance flips the sign once, here, per
docs/adr/0023), and returns a flat node map shaped like the frontend's
existing VdtNode contract.
"""

from collections import defaultdict
from typing import Optional

from sqlmodel import Session, col, select

from companies import load_business_units, sample_companies
from diagnostic_content import DIAGNOSTIC_CONTENT
from models import GLFact, GLNode, NodeType, NormalBalance


class UnknownScope(Exception):
    pass


def resolve_scope(scope: str) -> dict:
    """Returns which companies a scope covers, and whether that's partial."""
    sampled = sample_companies()
    sampled_codes = {c["code"] for c in sampled}
    business_units = load_business_units()

    for bu in business_units:
        company_codes = {c["code"] for c in bu["companies"]}
        if scope in company_codes:
            if scope not in sampled_codes:
                return {"kind": "company", "companies": [], "notYetModelled": True}
            return {"kind": "company", "companies": [scope], "notYetModelled": False, "partial": False}
        if bu["code"] == scope:
            bu_sampled = [c["code"] for c in sampled if c["bu"] == scope]
            return {
                "kind": "bu",
                "companies": bu_sampled,
                "notYetModelled": False,
                "partial": len(bu_sampled) < len(bu["companies"]),
                "sampledCompanyCount": len(bu_sampled),
                "totalCompanyCount": len(bu["companies"]),
            }

    raise UnknownScope(scope)


def _direction(actual: float, budget: float) -> str:
    variance = actual - budget
    if abs(variance) < 1e-9:
        return "neutral"
    return "favourable" if variance > 0 else "adverse"


def build_tree(session: Session, companies: list[str]) -> dict[str, dict]:
    nodes = session.exec(select(GLNode)).all()
    node_by_code = {n.code: n for n in nodes}
    children_by_parent: dict[str, list[str]] = defaultdict(list)
    for n in nodes:
        if n.parent_code:
            children_by_parent[n.parent_code].append(n.code)

    monthly: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(lambda: [0.0] * 12))
    if companies:
        # Selecting only the needed columns (rather than full GLFact rows)
        # skips ORM row hydration, the dominant cost for ~40k facts per scope.
        facts = session.exec(
            select(GLFact.code, GLFact.scenario, GLFact.month, GLFact.amount).where(col(GLFact.company).in_(companies))
        ).all()
        for code, scenario, month, amount in facts:
            monthly[code][scenario.value][month - 1] += amount

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
                # operational rows) — use the monthly average instead.
                entry = {
                    "monthlyActual": actual_monthly,
                    "actual": sum(actual_monthly) / 12,
                    "budget": sum(budget_monthly) / 12,
                    "priorYear": sum(prior_monthly) / 12,
                }
            else:
                sign = 1 if node.normal_balance == NormalBalance.CREDIT else -1
                monthly_actual = [v * sign for v in actual_monthly]
                entry = {
                    "monthlyActual": monthly_actual,
                    "actual": sum(monthly_actual),
                    "budget": sum(budget_monthly) * sign,
                    "priorYear": sum(prior_monthly) * sign,
                }
        else:
            child_codes = [c for c in children_by_parent.get(code, []) if node_by_code[c].node_type != NodeType.OPERATIONAL_DRIVER]
            child_entries = [compute(c) for c in child_codes]
            monthly_actual = [sum(e["monthlyActual"][i] for e in child_entries) for i in range(12)]
            entry = {
                "monthlyActual": monthly_actual,
                "actual": sum(monthly_actual),
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
            "direction": _direction(entry["actual"], entry["budget"]),
            "hasFullData": full_data is not None,
            **(full_data or {}),
        }
    return result
