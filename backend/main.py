import json
from typing import AsyncIterator, Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session, select

load_dotenv()

from company_tree import InvalidMonetaryScope, MissingCompanyCurrency, UnknownScope, build_company_tree, resolve_scope
from db import get_session
from driver_engine import DriverEngine
from gl_tree import build_tree, diff_subtree, subtree
from models import GLNode, PeriodType
from variance_analysis import VarianceAnalysisUnavailable, generate_variance_analysis
from periods import (
    UnknownPeriod,
    build_period_tree,
    calendar_month_label,
    load_period_hierarchy,
    ordered_month_codes_of_year,
    trailing_month_codes,
)
from trend_analysis import TrendAnalysisUnavailable, generate_trend_analysis
from vdt_sensitivity import SENSITIVITY_MAX_CYCLES, compute_sensitivity, terminal_driver_candidates
from vdt_tree import build_vdt_tree

VDT_COMPARISON_ROOT_TYPES = ("Reporting Root", "Reporting Node", "Activity Node")
VDT_TRENDS_ANCHOR = "V201000000"  # SOC Crew Cost, same fixed pilot anchor as VDT Variance Analysis/Reconciliation

app = FastAPI(title="Zeteo API")


def _resolve_monetary_scope(session: Session, scope: str) -> dict:
    try:
        return resolve_scope(session, scope)
    except UnknownScope:
        raise HTTPException(404, f"Unknown scope: {scope}")
    except InvalidMonetaryScope:
        raise HTTPException(422, f"Company scope required: {scope}")
    except MissingCompanyCurrency:
        raise HTTPException(500, f"Company has no currency: {scope}")


def _scope_meta(resolved: dict) -> dict:
    return {
        "scopeKind": "company",
        "currency": resolved["currency"],
        "partial": False,
        "sampledCompanyCount": len(resolved["companies"]),
        "totalCompanyCount": 1,
    }


@app.get("/api/companies")
def get_companies(session: Session = Depends(get_session)):
    return build_company_tree(session)


@app.get("/api/periods")
def get_periods(session: Session = Depends(get_session)):
    return build_period_tree(session)


@app.get("/api/gl/tree")
def get_gl_tree(scope: str, period: Optional[str] = None, session: Session = Depends(get_session)):
    if not session.exec(select(GLNode).limit(1)).first():
        raise HTTPException(500, "GL data not seeded — run `python backend/seed.py` first")

    resolved = _resolve_monetary_scope(session, scope)

    if resolved.get("notYetModelled"):
        return {"scope": scope, **_scope_meta(resolved), "notYetModelled": True, "nodes": {}}

    try:
        nodes = build_tree(session, resolved["companies"], period)
    except UnknownPeriod:
        raise HTTPException(404, f"Unknown period: {period}")
    return {
        "scope": scope,
        **_scope_meta(resolved),
        "notYetModelled": False,
        "period": period,
        "nodes": nodes,
    }


@app.get("/api/gl/comparison")
def get_gl_comparison(
    scope: str,
    node: str,
    period_a: str = Query(alias="periodA"),
    period_b: str = Query(alias="periodB"),
    session: Session = Depends(get_session),
):
    if not session.exec(select(GLNode).limit(1)).first():
        raise HTTPException(500, "GL data not seeded — run `python backend/seed.py` first")

    resolved = _resolve_monetary_scope(session, scope)

    if resolved.get("notYetModelled"):
        return {"scope": scope, **_scope_meta(resolved), "notYetModelled": True, "nodes": {}}

    period_by_code, _ = load_period_hierarchy(session)
    period_a_row = period_by_code.get(period_a)
    period_b_row = period_by_code.get(period_b)
    if period_a_row is None:
        raise HTTPException(404, f"Unknown period: {period_a}")
    if period_b_row is None:
        raise HTTPException(404, f"Unknown period: {period_b}")
    if period_a_row.period_type != period_b_row.period_type:
        raise HTTPException(400, "periodA and periodB must be the same grain (both Month, both Quarter, or both Year)")

    tree_a = build_tree(session, resolved["companies"], period_a)
    tree_b = build_tree(session, resolved["companies"], period_b)

    root = tree_a.get(node)
    if root is None:
        raise HTTPException(404, f"Unknown node: {node}")
    if root["nodeType"] not in ("Reporting Root", "Reporting Node"):
        raise HTTPException(400, f"{node} is a {root['nodeType']} — only a Reporting Root/Reporting Node can anchor a comparison")

    return {
        "scope": scope,
        **_scope_meta(resolved),
        "notYetModelled": False,
        "node": node,
        "periodA": period_a,
        "periodB": period_b,
        "nodes": diff_subtree(tree_a, tree_b, node),
    }


def _resolve_trailing_window(
    period_by_code: dict, period_children: dict, trailing_end: str
) -> list[str]:
    """Validates `trailing_end` is a known Month code and resolves its
    Trailing-mode window — shared by GET /api/vdt/tree and POST
    /api/vdt/trend-analysis (see docs/adr/0042), both of which need the same
    404 (unknown period) vs 400 (not a Month) distinction that
    trailing_month_codes() alone can't give (it only raises UnknownPeriod for
    both cases)."""
    anchor_row = period_by_code.get(trailing_end)
    if anchor_row is None:
        raise HTTPException(404, f"Unknown period: {trailing_end}")
    if anchor_row.period_type != PeriodType.MONTH:
        raise HTTPException(400, f"{trailing_end} is not a Month period")
    return trailing_month_codes(period_by_code, period_children, trailing_end)


@app.get("/api/vdt/tree")
def get_vdt_tree(
    scope: str,
    period: Optional[str] = None,
    trailing_end: Optional[str] = Query(default=None, alias="trailingEnd"),
    session: Session = Depends(get_session),
):
    """`period` (a Year/Quarter/Month code) is Financial Year mode, unchanged.
    `trailingEnd` (a Month code) is Trailing mode — see docs/adr/0042: the
    response's `months` field carries the resolved window (which can be
    shorter than 12 if the anchor is close to the earliest seeded data), so
    the frontend never has to re-derive it. The two are mutually exclusive in
    practice (the frontend never sends both), but `trailingEnd` simply wins
    if it somehow did, since Trailing mode is the more specific request.
    """
    if not session.exec(select(GLNode).limit(1)).first():
        raise HTTPException(500, "GL data not seeded — run `python backend/seed.py` first")

    resolved = _resolve_monetary_scope(session, scope)

    if resolved.get("notYetModelled"):
        return {"scope": scope, **_scope_meta(resolved), "notYetModelled": True, "nodes": {}}

    if trailing_end is not None:
        period_by_code, period_children = load_period_hierarchy(session)
        window_codes = _resolve_trailing_window(period_by_code, period_children, trailing_end)
        nodes = build_vdt_tree(session, resolved["companies"], month_codes=window_codes)
        return {
            "scope": scope,
            **_scope_meta(resolved),
            "notYetModelled": False,
            "period": None,
            "months": window_codes,
            "nodes": nodes,
        }

    try:
        nodes = build_vdt_tree(session, resolved["companies"], period)
    except UnknownPeriod:
        raise HTTPException(404, f"Unknown period: {period}")
    return {
        "scope": scope,
        **_scope_meta(resolved),
        "notYetModelled": False,
        "period": period,
        "nodes": nodes,
    }


def _vdt_comparison_payload(
    session: Session,
    scope: str,
    node: str,
    period_a: str,
    period_b: str,
    ytd: bool,
) -> dict:
    """Shared by GET /api/vdt/comparison and POST /api/vdt/variance-analysis — both
    need the same resolved-scope, period-validated, diffed VDT subtree (see
    docs/adr/0034). Raises HTTPException on any resolution failure."""
    if not session.exec(select(GLNode).limit(1)).first():
        raise HTTPException(500, "GL data not seeded — run `python backend/seed.py` first")

    resolved = _resolve_monetary_scope(session, scope)

    if resolved.get("notYetModelled"):
        return {"scope": scope, **_scope_meta(resolved), "notYetModelled": True, "nodes": {}}

    period_by_code, _ = load_period_hierarchy(session)
    period_a_row = period_by_code.get(period_a)
    period_b_row = period_by_code.get(period_b)
    if period_a_row is None:
        raise HTTPException(404, f"Unknown period: {period_a}")
    if period_b_row is None:
        raise HTTPException(404, f"Unknown period: {period_b}")
    if period_a_row.period_type != period_b_row.period_type:
        raise HTTPException(400, "periodA and periodB must be the same grain (both Month, both Quarter, or both Year)")

    tree_a = build_vdt_tree(session, resolved["companies"], period_a, ytd=ytd)
    tree_b = build_vdt_tree(session, resolved["companies"], period_b, ytd=ytd)

    root = tree_a.get(node)
    if root is None:
        raise HTTPException(404, f"Unknown node: {node}")
    if root["nodeType"] not in VDT_COMPARISON_ROOT_TYPES:
        raise HTTPException(400, f"{node} is a {root['nodeType']} — only {'/'.join(VDT_COMPARISON_ROOT_TYPES)} can anchor a comparison")

    return {
        "scope": scope,
        **_scope_meta(resolved),
        "notYetModelled": False,
        "node": node,
        "periodA": period_a,
        "periodB": period_b,
        "ytd": ytd,
        "nodes": diff_subtree(tree_a, tree_b, node),
    }


@app.get("/api/vdt/comparison")
def get_vdt_comparison(
    scope: str,
    node: str,
    period_a: str = Query(alias="periodA"),
    period_b: str = Query(alias="periodB"),
    ytd: bool = False,
    session: Session = Depends(get_session),
):
    return _vdt_comparison_payload(session, scope, node, period_a, period_b, ytd)


@app.post("/api/vdt/variance-analysis")
def post_vdt_variance_analysis(
    scope: str,
    node: str,
    period_a: str = Query(alias="periodA"),
    period_b: str = Query(alias="periodB"),
    ytd: bool = False,
    session: Session = Depends(get_session),
):
    payload = _vdt_comparison_payload(session, scope, node, period_a, period_b, ytd)
    if payload.get("notYetModelled"):
        raise HTTPException(404, "No VDT data modelled for the selected company yet")

    cache_key = (scope, node, period_a, period_b, ytd)
    try:
        variance_analysis = generate_variance_analysis(
            cache_key, node, payload["nodes"], period_a, period_b, currency=payload["currency"]
        )
    except VarianceAnalysisUnavailable as exc:
        raise HTTPException(503, str(exc))
    return {"varianceAnalysis": variance_analysis}


@app.post("/api/vdt/trend-analysis")
def post_vdt_trend_analysis(
    scope: str,
    year: Optional[str] = None,
    trailing_end: Optional[str] = Query(default=None, alias="trailingEnd"),
    scenario: str = "actual",
    session: Session = Depends(get_session),
):
    """Whole-window MoM Trend Analysis narrative for VDT Trends — see
    docs/adr/0040 and docs/adr/0042. Always reads the fixed pilot anchor (SOC
    Crew Cost) and the underlying non-cumulative monthly series, regardless of
    the screen's Cumulative toggle — flagging needs monthly deltas, which a
    cumulative series would make meaningless. Exactly one of `year`
    (Financial Year mode) or `trailingEnd` (Trailing mode, a Month code
    anchor) must be given.
    """
    if scenario not in ("actual", "budget"):
        raise HTTPException(400, "scenario must be 'actual' or 'budget'")
    if (year is None) == (trailing_end is None):
        raise HTTPException(400, "exactly one of year or trailingEnd must be provided")

    if not session.exec(select(GLNode).limit(1)).first():
        raise HTTPException(500, "GL data not seeded — run `python backend/seed.py` first")

    resolved = _resolve_monetary_scope(session, scope)
    if resolved.get("notYetModelled"):
        raise HTTPException(404, "No VDT data modelled for the selected company yet")

    period_by_code, period_children = load_period_hierarchy(session)

    if trailing_end is not None:
        window_codes = _resolve_trailing_window(period_by_code, period_children, trailing_end)
        tree = build_vdt_tree(session, resolved["companies"], month_codes=window_codes)
        month_labels = [calendar_month_label(period_by_code[c]) for c in window_codes]
        window_label = f"the trailing {len(window_codes)} months ending {month_labels[-1]}"
    else:
        year_row = period_by_code.get(year)
        if year_row is None:
            raise HTTPException(404, f"Unknown period: {year}")
        if year_row.period_type != PeriodType.YEAR:
            raise HTTPException(400, f"{year} is not a fiscal-year period")
        window_codes = ordered_month_codes_of_year(period_by_code, period_children, year)
        tree = build_vdt_tree(session, resolved["companies"], year)
        month_labels = [period_by_code[c].label.split(" ")[0] for c in window_codes]
        window_label = f"fiscal year {year}"

    # Keyed on the resolved window, not the request's own year/trailingEnd
    # identifier — a Financial Year request and a Trailing request that
    # happen to resolve to the same months share one cache entry (see
    # docs/adr/0042).
    cache_key = (scope, tuple(window_codes), scenario)

    if VDT_TRENDS_ANCHOR not in tree:
        raise HTTPException(404, f"Anchor {VDT_TRENDS_ANCHOR} missing from VDT tree")

    try:
        result = generate_trend_analysis(cache_key, tree, VDT_TRENDS_ANCHOR, scenario, window_label, month_labels)
    except TrendAnalysisUnavailable as exc:
        raise HTTPException(503, str(exc))
    return {"trendAnalysis": result}


@app.get("/api/vdt/reconciliation")
def get_vdt_reconciliation(
    scope: str, node: str, period: Optional[str] = None, ytd: bool = False, session: Session = Depends(get_session)
):
    """VDT-hierarchy subtree at `node`, plus the Accounting nodes needed to
    show each Posting Activity Account leaf's FA GL anchor alongside it — see
    docs/adr/0033, docs/adr/0037. `node` anchors in the VDT tree (it's
    routinely a VDT-only Activity Node, e.g. SOC Crew Cost, with no same-code
    Accounting node at all), so `accounting.nodes` is not a subtree of the
    same code — it's just the specific anchor nodes the VDT subtree's leaves
    point to, keyed by their own GL code. No delta/polarity coloring: the two
    hierarchies are independent estimates that aren't required to reconcile —
    the gap between them is the point, not something to score.
    """
    if not session.exec(select(GLNode).limit(1)).first():
        raise HTTPException(500, "GL data not seeded — run `python backend/seed.py` first")

    resolved = _resolve_monetary_scope(session, scope)

    if resolved.get("notYetModelled"):
        return {
            "scope": scope,
            **_scope_meta(resolved),
            "notYetModelled": True,
            "node": node,
            "accounting": {"nodes": {}},
            "vdt": {"nodes": {}},
        }

    try:
        accounting_tree = build_tree(session, resolved["companies"], period, ytd=ytd)
        vdt_tree = build_vdt_tree(session, resolved["companies"], period, ytd=ytd)
    except UnknownPeriod:
        raise HTTPException(404, f"Unknown period: {period}")

    root = vdt_tree.get(node)
    if root is None:
        raise HTTPException(404, f"Unknown node: {node}")
    if root["nodeType"] not in VDT_COMPARISON_ROOT_TYPES:
        raise HTTPException(
            400, f"{node} is a {root['nodeType']} — only {'/'.join(VDT_COMPARISON_ROOT_TYPES)} can anchor a reconciliation"
        )

    vdt_nodes = subtree(vdt_tree, node)
    anchor_codes = {
        n["faGlCode"]
        for n in vdt_nodes.values()
        if n["nodeType"] == "Posting Activity Account" and n.get("faGlCode")
    }
    accounting_nodes = {code: accounting_tree[code] for code in anchor_codes if code in accounting_tree}

    return {
        "scope": scope,
        **_scope_meta(resolved),
        "notYetModelled": False,
        "node": node,
        "period": period,
        "ytd": ytd,
        "accounting": {"nodes": accounting_nodes},
        "vdt": {"nodes": vdt_nodes},
    }


async def _sensitivity_event_stream(events, request: Request, augment_result) -> AsyncIterator[bytes]:
    """Drives `compute_sensitivity()`'s generator, checking
    `request.is_disconnected()` after each yielded event (an "each
    per-driver-direction rerun" — a whole window's months batch into one
    `compute_npat_with_overrides` call, see vdt_sensitivity.py's
    `SENSITIVITY_MAX_CYCLES` note) so an abandoned run performs no further
    compute — `events` is a lazy generator, so simply ending this loop
    (never calling `next()` again) is enough to stop it early. Module-level
    (not a nested closure) so it's directly unit-testable with a fake
    `request` whose `is_disconnected()` always returns True, without needing
    a live TestClient connection to actually sever — see
    test_vdt_sensitivity.py.
    """
    try:
        for event in events:
            if await request.is_disconnected():
                break
            yield f"data: {json.dumps(augment_result(event))}\n\n".encode()
    except Exception as exc:
        yield f"data: {json.dumps({'type': 'error', 'detail': str(exc)})}\n\n".encode()


class SensitivityRequest(BaseModel):
    scope: str  # Company code
    scopeNode: str  # VDT node code (frontend sends the resolved code; whole-book default = the Reporting Root)
    bumpPct: float  # 1..20 inclusive
    scenario: str = "actual"  # 'actual' | 'budget'
    year: Optional[str] = None  # Financial Year mode (Year code)
    trailingEnd: Optional[str] = None  # Trailing mode (anchor Month code)


@app.post("/api/vdt/sensitivity")
def post_vdt_sensitivity(payload: SensitivityRequest, request: Request, session: Session = Depends(get_session)):
    """VDT Sensitivity Analysis — see docs/adr/0043. First streaming-response
    endpoint in this codebase: validation happens as ordinary HTTP errors
    before the SSE stream ever opens (so a client never has to parse an error
    out of an event frame), then the elasticity run streams `progress` events
    followed by exactly one `result` event.
    """
    if not (1.0 <= payload.bumpPct <= 20.0):
        raise HTTPException(422, "bump percent must be between 1 and 20")
    if payload.scenario not in ("actual", "budget"):
        raise HTTPException(400, "scenario must be 'actual' or 'budget'")
    if (payload.year is None) == (payload.trailingEnd is None):
        raise HTTPException(400, "exactly one of year or trailingEnd must be provided")

    if not session.exec(select(GLNode).limit(1)).first():
        raise HTTPException(500, "GL data not seeded — run `python backend/seed.py` first")

    resolved = _resolve_monetary_scope(session, payload.scope)
    if resolved.get("notYetModelled"):
        raise HTTPException(404, "No VDT data modelled for the selected company yet")

    period_by_code, period_children = load_period_hierarchy(session)

    if payload.trailingEnd is not None:
        window_codes = _resolve_trailing_window(period_by_code, period_children, payload.trailingEnd)
        month_labels = [calendar_month_label(period_by_code[c]) for c in window_codes]
        window_label = f"trailing {len(window_codes)} months ending {month_labels[-1]}" if month_labels else "trailing window"
        vdt_nodes = build_vdt_tree(session, resolved["companies"], month_codes=window_codes)
    else:
        year_row = period_by_code.get(payload.year)
        if year_row is None:
            raise HTTPException(404, f"Unknown period: {payload.year}")
        if year_row.period_type != PeriodType.YEAR:
            raise HTTPException(400, f"{payload.year} is not a fiscal-year period")
        window_codes = ordered_month_codes_of_year(period_by_code, period_children, payload.year)
        month_labels = [period_by_code[c].label.split(" ")[0] for c in window_codes]
        window_label = f"fiscal year {payload.year}"
        vdt_nodes = build_vdt_tree(session, resolved["companies"], payload.year)

    scope_node = vdt_nodes.get(payload.scopeNode)
    if scope_node is None:
        raise HTTPException(404, f"Unknown node: {payload.scopeNode}")

    root_code = next((code for code, node in vdt_nodes.items() if node["nodeType"] == "Reporting Root"), None)
    if root_code is None:
        raise HTTPException(500, "VDT tree has no Reporting Root")

    company = resolved["companies"][0]
    # ONE baseline DriverEngine, reused read-only for candidate discovery and
    # baseline driver values (see docs/adr/0043) — every bumped rerun below
    # still builds its OWN fresh engine via compute_npat_with_overrides.
    engine = DriverEngine(session, resolved["companies"], window_codes)
    candidates = terminal_driver_candidates(engine, payload.scopeNode, vdt_nodes)

    total = len(candidates) * 2
    if total > SENSITIVITY_MAX_CYCLES:
        raise HTTPException(422, f"sensitivity run too large: {total} cycles, cap {SENSITIVITY_MAX_CYCLES}")

    generator = compute_sensitivity(
        session, company, payload.scenario, window_codes, root_code, candidates, payload.bumpPct, engine, total
    )

    def augment_result(event: dict) -> dict:
        if event["type"] != "result":
            return event
        return {
            **event,
            "scope": payload.scope,
            "scopeNode": payload.scopeNode,
            "scopeName": scope_node["name"],
            "currency": resolved["currency"],
            "bumpPct": payload.bumpPct,
            "monthLabels": month_labels,
            "windowLabel": window_label,
        }

    return StreamingResponse(
        _sensitivity_event_stream(generator, request, augment_result),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )
