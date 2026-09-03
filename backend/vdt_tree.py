"""Server-side rollup of the VDT (activity-based) hierarchy — see docs/adr/0033.

Structurally mirrors gl_tree.build_tree(): identical period/company scoping
(load_monthly/scoped_sum/DriverEngine), identical bottom-up compute shape,
directly sharing compute_gl_leaf()/sum_children_entry() with it rather than
duplicating them. What's VDT-specific is the adjacency: an Activity Node's
`parent_code` can point at an existing general_ledger.code (e.g. PNL-0011
Cost of Revenue) — wherever that happens, this tree's children at that code
are REPLACED WHOLESALE by the Activity Node(s), not unioned with the GL
code's ordinary Reporting-Node children (never mutating general_ledger
itself — this is a VDT-only view of the adjacency). Everywhere else, GL
children pass through unmodified. A direct consequence: any GL subtree that
was hanging off a now-overridden parent (e.g. the old Manpower Cost branch
under Cost of Revenue, before Crew Cost's Activity Nodes were seeded there)
becomes unreachable from NPAT in this tree and simply doesn't appear in the
result — an honest partial state, not a bug to paper over (see the ADR's
decision log).
"""

import logging
from collections import defaultdict
from typing import Optional

from sqlmodel import Session, select

from diagnostic_content import DIAGNOSTIC_CONTENT
from driver_engine import DriverEngine
from gl_tree import (
    _direction,
    _prior_year_code,
    _stitch_driver_nodes,
    _year_of,
    compute_gl_leaf,
    load_monthly,
    scoped_sum,
    sum_children_entry,
)
from models import ActivityNode, GLNode, NodeType, NormalBalance, PeriodType, PostingActivityAccount
from periods import load_period_hierarchy, month_indices_for

logger = logging.getLogger(__name__)

ACTIVITY_NODE_TYPE = "Activity Node"
POSTING_ACTIVITY_ACCOUNT_TYPE = "Posting Activity Account"


def _compute_posting_activity_account(
    code: str,
    account: PostingActivityAccount,
    engine: DriverEngine,
    gl_by_code: dict[str, GLNode],
    scope_indices: Optional[set[int]],
) -> dict:
    """A Posting Activity Account is always Driver-Formula-driven — no raw
    fact fallback, unlike a GL leaf (see docs/adr/0033). Sign is derived from
    its FA GL anchor's own normal_balance (a display/reconciliation anchor,
    not identity — see PostingActivityAccount's docstring in models.py).
    No prior-year source of its own (no raw fact table) — zero, same
    accepted gap a driven GL leaf already has today.
    """
    anchor = gl_by_code.get(account.fa_gl_code)
    sign = 1 if anchor is not None and anchor.normal_balance == NormalBalance.CREDIT else -1

    if engine.is_driven(code):
        actual_monthly = engine.target_value(code, "actual")
        budget_monthly = engine.target_value(code, "budget")
    else:
        logger.warning("Posting Activity Account %s has no Driver Formula bound to it — seed data gap", code)
        actual_monthly = [0.0] * 12
        budget_monthly = [0.0] * 12

    monthly_actual = [v * sign for v in actual_monthly]
    monthly_budget = [v * sign for v in budget_monthly]
    return {
        "monthlyActual": monthly_actual,
        "monthlyPriorYear": [0.0] * 12,
        "actual": scoped_sum(monthly_actual, scope_indices),
        "budget": scoped_sum(monthly_budget, scope_indices),
        "priorYear": 0.0,
    }


def build_vdt_tree(session: Session, companies: list[str], period_code: Optional[str] = None) -> dict[str, dict]:
    gl_nodes = session.exec(select(GLNode)).all()
    gl_by_code = {n.code: n for n in gl_nodes}
    activity_nodes = session.exec(select(ActivityNode)).all()
    activity_by_code = {n.code: n for n in activity_nodes}
    accounts = session.exec(select(PostingActivityAccount)).all()
    account_by_code = {n.code: n for n in accounts}

    # --- adjacency ---
    children_by_parent: dict[str, list[str]] = defaultdict(list)
    for n in gl_nodes:
        if n.parent_code:
            children_by_parent[n.parent_code].append(n.code)

    # Top-level Activity Nodes group by the GL code they attach to.
    activity_roots_by_gl_parent: dict[str, list[str]] = defaultdict(list)
    for n in activity_nodes:
        if n.parent_code in gl_by_code:
            activity_roots_by_gl_parent[n.parent_code].append(n.code)

    # Wholesale replace at every GL attachment point (see module docstring).
    for gl_parent_code, activity_codes in activity_roots_by_gl_parent.items():
        children_by_parent[gl_parent_code] = sorted(activity_codes)

    # Activity Node -> Activity Node (interior nesting) and Activity Node ->
    # Posting Activity Account — VDT-only edges, plain appends.
    for n in activity_nodes:
        if n.parent_code in activity_by_code:
            children_by_parent[n.parent_code].append(n.code)
    for n in accounts:
        children_by_parent[n.parent_code].append(n.code)

    # --- period/company scoping (identical to build_tree()) ---
    period_by_code, period_children = load_period_hierarchy(session)
    years = sorted((p for p in period_by_code.values() if p.period_type == PeriodType.YEAR), key=lambda p: p.order)
    year_code = _year_of(period_by_code, period_code) if period_code is not None else (years[-1].code if years else None)
    prior_year_code = _prior_year_code(period_by_code, year_code) if year_code else None
    scope_indices = month_indices_for(period_by_code, period_children, period_code)

    def scoped_sum_local(monthly_values: list[float]) -> float:
        return scoped_sum(monthly_values, scope_indices)

    monthly = load_monthly(session, companies, period_by_code, period_children, year_code)
    prior_monthly = load_monthly(session, companies, period_by_code, period_children, prior_year_code)

    period_len = len(scope_indices) if scope_indices is not None else 12
    engine = DriverEngine(session, companies, year_code)

    computed: dict[str, dict] = {}

    def compute(code: str) -> dict:
        if code in computed:
            return computed[code]

        if code in account_by_code:
            entry = _compute_posting_activity_account(code, account_by_code[code], engine, gl_by_code, scope_indices)
        elif code in gl_by_code and gl_by_code[code].node_type == NodeType.POSTING_GL_ACCOUNT:
            entry = compute_gl_leaf(gl_by_code[code], engine, monthly, prior_monthly, scope_indices)
        else:
            # GL Reporting Root/Node (unmodified or GL-passthrough) or Activity
            # Node — both are just "sum my children" in this tree.
            child_entries = [compute(c) for c in children_by_parent.get(code, [])]
            entry = sum_children_entry(child_entries)

        computed[code] = entry
        return entry

    for code, node in gl_by_code.items():
        if node.node_type == NodeType.REPORTING_ROOT:
            compute(code)

    # Only codes actually reached from a Reporting Root are real in this tree
    # — a GL subtree hanging off a now-overridden parent is unreachable and
    # deliberately absent (see module docstring), not an error.
    result: dict[str, dict] = {}
    for code, entry in computed.items():
        if code in gl_by_code:
            node = gl_by_code[code]
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
                extra_nodes, formula_ids = _stitch_driver_nodes(engine, code, code, scoped_sum_local, period_len)
                result[code]["childIds"] = result[code]["childIds"] + formula_ids
                result.update(extra_nodes)

        elif code in activity_by_code:
            node = activity_by_code[code]
            result[code] = {
                "id": code,
                "name": node.description,
                "parentId": node.parent_code,
                "childIds": list(children_by_parent.get(code, [])),
                "nodeType": ACTIVITY_NODE_TYPE,
                "unit": "RM_M",
                "actual": round(entry["actual"], 3),
                "budget": round(entry["budget"], 3),
                "priorYear": round(entry["priorYear"], 3),
                "monthlyActual": [round(v, 3) for v in entry["monthlyActual"]],
                "monthlyPriorYear": [round(v, 3) for v in entry["monthlyPriorYear"]],
                "direction": _direction(entry["actual"], entry["budget"]),
                "hasFullData": False,
            }

        elif code in account_by_code:
            node = account_by_code[code]
            result[code] = {
                "id": code,
                "name": node.description,
                "parentId": node.parent_code,
                "childIds": list(children_by_parent.get(code, [])),
                "nodeType": POSTING_ACTIVITY_ACCOUNT_TYPE,
                "unit": "RM_M",
                "faGlCode": node.fa_gl_code,
                "actual": round(entry["actual"], 3),
                "budget": round(entry["budget"], 3),
                "priorYear": round(entry["priorYear"], 3),
                "monthlyActual": [round(v, 3) for v in entry["monthlyActual"]],
                "monthlyPriorYear": [round(v, 3) for v in entry["monthlyPriorYear"]],
                "direction": _direction(entry["actual"], entry["budget"]),
                "hasFullData": False,
            }
            if engine.is_driven(code):
                extra_nodes, formula_ids = _stitch_driver_nodes(engine, code, code, scoped_sum_local, period_len)
                result[code]["childIds"] = result[code]["childIds"] + formula_ids
                result.update(extra_nodes)

    return result
