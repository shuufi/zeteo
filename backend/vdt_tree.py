"""Server-side rollup of the VDT hierarchy — see docs/adr/0033.

Structurally mirrors gl_tree.build_tree(): identical period/company scoping
(load_monthly/scoped_sum/DriverEngine), identical bottom-up compute shape,
directly sharing compute_gl_leaf()/sum_children_entry() with it rather than
duplicating them. What's VDT-specific is the adjacency: a VDT Hierarchy Node's
`parent_code` can point at an existing general_ledger.code (e.g. PNL-0011
Cost of Revenue) — wherever that happens, this tree's children at that code
are REPLACED WHOLESALE by the VDT Hierarchy Node(s), not unioned with the GL
code's ordinary Reporting-Node children (never mutating general_ledger
itself — this is a VDT-only view of the adjacency). Everywhere else, GL
children pass through unmodified. A direct consequence: any GL subtree that
was hanging off a now-overridden parent (e.g. the old Manpower Cost branch
under Cost of Revenue, before Crew Cost's VDT Hierarchy Nodes were seeded
there) becomes unreachable from NPAT in this tree and simply doesn't appear
in the result — an honest partial state, not a bug to paper over (see the
ADR's decision log).
"""

import logging
from collections import defaultdict
from decimal import Decimal
from typing import Optional

from sqlmodel import Session, select

from diagnostic_content import DIAGNOSTIC_CONTENT
from driver_engine import DriverEngine
from gl_tree import (
    _direction,
    _money_json,
    _prior_year_code,
    _stitch_driver_nodes,
    _year_of,
    compute_gl_leaf,
    load_monthly,
    scoped_sum,
    sum_children_entry,
    ZERO,
)
from models import GLNode, NodeType, NormalBalance, PeriodType, VdtAccount, VdtHierarchy
from periods import load_period_hierarchy, month_indices_for, ordered_month_codes_of_year, ytd_month_indices_for

logger = logging.getLogger(__name__)

VDT_HIERARCHY_NODE_TYPE = "VDT Hierarchy Node"
VDT_ACCOUNT_TYPE = "VDT Account"


def _compute_vdt_account(
    code: str,
    account: VdtAccount,
    engine: DriverEngine,
    gl_by_code: dict[str, GLNode],
    scope_indices: Optional[set[int]],
    width: int,
) -> dict:
    """A VDT Account is always Driver-Formula-driven — no raw fact fallback,
    unlike a GL leaf (see docs/adr/0033). Sign is derived from its FA GL
    anchor's own normal_balance (a display/reconciliation anchor, not
    identity — see VdtAccount's docstring in models.py). No prior-year source
    of its own (no raw fact table) — zero, same accepted gap a driven GL leaf
    already has today.
    """
    anchor = gl_by_code.get(account.fa_gl_code)
    sign = 1 if anchor is not None and anchor.normal_balance == NormalBalance.CREDIT else -1

    if engine.is_driven(code):
        actual_monthly = engine.target_value(code, "actual")
        budget_monthly = engine.target_value(code, "budget")
    else:
        logger.warning("VDT Account %s has no Driver Formula bound to it — seed data gap", code)
        actual_monthly = [ZERO] * width
        budget_monthly = [ZERO] * width

    monthly_actual = [v * sign for v in actual_monthly]
    monthly_budget = [v * sign for v in budget_monthly]
    return {
        "monthlyActual": monthly_actual,
        "monthlyBudget": monthly_budget,
        "monthlyPriorYear": [ZERO] * width,
        "actual": scoped_sum(monthly_actual, scope_indices),
        "budget": scoped_sum(monthly_budget, scope_indices),
        "priorYear": ZERO,
    }


def build_vdt_tree(
    session: Session,
    companies: list[str],
    period_code: Optional[str] = None,
    ytd: bool = False,
    month_codes: Optional[list[str]] = None,
    engine: Optional[DriverEngine] = None,
) -> dict[str, dict]:
    """`engine`, if given, is used in place of constructing a fresh
    `DriverEngine` internally — the hook `vdt_sensitivity.py`'s override
    primitive needs (see docs/adr/0043): NPAT is a GL Reporting Root, never
    itself a `DriverFormula` target, so `DriverEngine.target_value()` alone
    can't recompute it (it only sums formulas bound to the exact target code
    asked for) — only this whole-tree rollup walk can, since NPAT's real
    value is raw GL leaf facts (unaffected by a Driver override) plus
    Driver-Formula-driven VDT Account leaves (affected) summed
    bottom-up. Passing a pre-built engine here (with an in-memory `facts`
    overlay already applied — see `compute_npat_with_overrides`) is what lets
    that overlay actually reach NPAT, matching the ADR's "re-run DriverEngine
    up through vdt_tree to NPAT" compute method. `None` (every other caller)
    preserves today's behaviour exactly — a fresh engine built from
    `companies`/`month_codes` as before.
    """
    gl_nodes = session.exec(select(GLNode)).all()
    gl_by_code = {n.code: n for n in gl_nodes}
    vdt_hierarchy_nodes = session.exec(select(VdtHierarchy)).all()
    vdt_hierarchy_by_code = {n.code: n for n in vdt_hierarchy_nodes}
    vdt_accounts = session.exec(select(VdtAccount)).all()
    vdt_account_by_code = {n.code: n for n in vdt_accounts}

    # --- adjacency ---
    children_by_parent: dict[str, list[str]] = defaultdict(list)
    for n in gl_nodes:
        if n.parent_code:
            children_by_parent[n.parent_code].append(n.code)

    # Top-level VDT Hierarchy Nodes group by the GL code they attach to.
    vdt_hierarchy_roots_by_gl_parent: dict[str, list[str]] = defaultdict(list)
    for n in vdt_hierarchy_nodes:
        if n.parent_code in gl_by_code:
            vdt_hierarchy_roots_by_gl_parent[n.parent_code].append(n.code)

    # Wholesale replace at every GL attachment point (see module docstring).
    for gl_parent_code, vdt_hierarchy_codes in vdt_hierarchy_roots_by_gl_parent.items():
        children_by_parent[gl_parent_code] = sorted(vdt_hierarchy_codes)

    # VDT Hierarchy Node -> VDT Hierarchy Node (interior nesting) and VDT Hierarchy Node ->
    # VDT Account — VDT-only edges, plain appends.
    for n in vdt_hierarchy_nodes:
        if n.parent_code in vdt_hierarchy_by_code:
            children_by_parent[n.parent_code].append(n.code)
    for n in vdt_accounts:
        children_by_parent[n.parent_code].append(n.code)

    # --- period/company scoping (identical to build_tree(), except the
    # Trailing-mode branch below — see docs/adr/0042) ---
    period_by_code, period_children = load_period_hierarchy(session)
    if month_codes is not None:
        # Trailing mode: caller already resolved an explicit window (possibly
        # spanning two fiscal years' sibling Year roots), so none of the
        # single-Year machinery below applies. No prior-year series (that
        # concept means "the same window one fiscal year back", which ADR-0042
        # doesn't define for an arbitrary trailing window) and no sub-window
        # scope_indices (Trailing mode's Cumulative toggle is computed
        # client-side from the full monthlyActual array, unlike Financial Year
        # mode's YTD, which nothing here still calls YTD for VDT Trends itself).
        window_codes: Optional[list[str]] = month_codes
        prior_window_codes: Optional[list[str]] = None
        scope_indices = None
    else:
        years = sorted((p for p in period_by_code.values() if p.period_type == PeriodType.YEAR), key=lambda p: p.order)
        year_code = _year_of(period_by_code, period_code) if period_code is not None else (years[-1].code if years else None)
        prior_year_code = _prior_year_code(period_by_code, year_code) if year_code else None
        window_codes = ordered_month_codes_of_year(period_by_code, period_children, year_code) if year_code else None
        prior_window_codes = (
            ordered_month_codes_of_year(period_by_code, period_children, prior_year_code) if prior_year_code else None
        )
        scope_indices = (
            ytd_month_indices_for(period_by_code, period_children, period_code)
            if ytd
            else month_indices_for(period_by_code, period_children, period_code)
        )

    def scoped_sum_local(monthly_values: list[Decimal]) -> Decimal:
        return scoped_sum(monthly_values, scope_indices)

    width = len(window_codes) if window_codes else 12
    monthly = load_monthly(session, companies, window_codes)
    prior_monthly = load_monthly(session, companies, prior_window_codes)

    period_len = len(scope_indices) if scope_indices is not None else width
    if engine is None:
        engine = DriverEngine(session, companies, window_codes)

    computed: dict[str, dict] = {}

    def compute(code: str) -> dict:
        if code in computed:
            return computed[code]

        if code in vdt_account_by_code:
            entry = _compute_vdt_account(code, vdt_account_by_code[code], engine, gl_by_code, scope_indices, width)
        elif code in gl_by_code and gl_by_code[code].node_type == NodeType.POSTING_GL_ACCOUNT:
            entry = compute_gl_leaf(gl_by_code[code], engine, monthly, prior_monthly, scope_indices, width)
        else:
            # GL Reporting Root/Node (unmodified or GL-passthrough) or VDT
            # Hierarchy node — both are just "sum my children" in this tree.
            child_entries = [compute(c) for c in children_by_parent.get(code, [])]
            entry = sum_children_entry(child_entries, width)

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
            if node.node_type == NodeType.POSTING_GL_ACCOUNT and engine.is_driven(code):
                extra_nodes, formula_ids = _stitch_driver_nodes(engine, code, code, scoped_sum_local, period_len)
                result[code]["childIds"] = result[code]["childIds"] + formula_ids
                result.update(extra_nodes)

        elif code in vdt_hierarchy_by_code:
            node = vdt_hierarchy_by_code[code]
            result[code] = {
                "id": code,
                "name": node.description,
                "parentId": node.parent_code,
                "childIds": list(children_by_parent.get(code, [])),
                "nodeType": VDT_HIERARCHY_NODE_TYPE,
                "unit": "money",
                "actual": _money_json(entry["actual"]),
                "budget": _money_json(entry["budget"]),
                "priorYear": _money_json(entry["priorYear"]),
                "monthlyActual": [_money_json(v) for v in entry["monthlyActual"]],
                "monthlyBudget": [_money_json(v) for v in entry["monthlyBudget"]],
                "monthlyPriorYear": [_money_json(v) for v in entry["monthlyPriorYear"]],
                "direction": _direction(entry["actual"], entry["budget"]),
                "hasFullData": False,
            }

        elif code in vdt_account_by_code:
            node = vdt_account_by_code[code]
            result[code] = {
                "id": code,
                "name": node.description,
                "parentId": node.parent_code,
                "childIds": list(children_by_parent.get(code, [])),
                "nodeType": VDT_ACCOUNT_TYPE,
                "unit": "money",
                "faGlCode": node.fa_gl_code,
                "actual": _money_json(entry["actual"]),
                "budget": _money_json(entry["budget"]),
                "priorYear": _money_json(entry["priorYear"]),
                "monthlyActual": [_money_json(v) for v in entry["monthlyActual"]],
                "monthlyBudget": [_money_json(v) for v in entry["monthlyBudget"]],
                "monthlyPriorYear": [_money_json(v) for v in entry["monthlyPriorYear"]],
                "direction": _direction(entry["actual"], entry["budget"]),
                "hasFullData": False,
            }
            if engine.is_driven(code):
                extra_nodes, formula_ids = _stitch_driver_nodes(engine, code, code, scoped_sum_local, period_len)
                result[code]["childIds"] = result[code]["childIds"] + formula_ids
                result.update(extra_nodes)

    return result
