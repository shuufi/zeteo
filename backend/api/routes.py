import json
from typing import AsyncIterator, Optional

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session, select

load_dotenv()

from backend.organization.hierarchy import (
    InvalidMonetaryScope,
    MissingCompanyCurrency,
    UnknownScope,
    build_company_hierarchy_tree,
    build_company_tree,
    resolve_scope,
)
from backend.infrastructure.db import get_session
from backend.drivers.engine import DriverEngine
from backend.accounting.tree import build_gl_master_tree, build_tree, diff_subtree, periods_of_year, subtree
from backend.accounting.models import GLAccount, GLHierarchy
from backend.organization.models import HierarchyKind
from backend.diagnostics.variance_analysis import VarianceAnalysisUnavailable, generate_variance_analysis
from backend.calendar.periods import (
    UnknownPeriod,
    build_period_tree,
    calendar_month_label,
    load_periods,
    load_years,
    trailing_periods,
)
from backend.diagnostics.trend_analysis import TrendAnalysisUnavailable, generate_trend_analysis
from backend.diagnostics.sensitivity import SENSITIVITY_MAX_CYCLES, compute_sensitivity, terminal_driver_candidates
from backend.vdt.tree import build_vdt_tree

VDT_COMPARISON_ROOT_TYPES = ("Reporting Root", "Reporting Node", "VDT Hierarchy Node")
VDT_TRENDS_ANCHOR = "V201000000"  # SOC Crew Cost, same fixed pilot anchor as VDT Variance Analysis/Reconciliation

router = APIRouter()


def _grain(quarter: Optional[int], month: Optional[int]) -> str:
    if month is not None:
        return "Month"
    if quarter is not None:
        return "Quarter"
    return "Year"


def _period_label(session: Session, year: int, quarter: Optional[int], month: Optional[int]) -> str:
    if month is not None:
        periods = load_periods(session)
        period_row = periods.get(month)
        month_label = period_row.label[:3] if period_row else str(month)
        return f"{month_label} {year}"
    if quarter is not None:
        return f"Q{quarter} {year}"
    return str(year)


def _gl_seeded(session: Session) -> bool:
    """GL is now two tables (docs/adr/0048) seeded atomically together by
    seed.py's single commit — checking only one would still be correct today,
    but checking both keeps this guard's own claim ("GL data is seeded")
    true independent of that assumption holding forever."""
    return bool(session.exec(select(GLHierarchy).limit(1)).first()) and bool(
        session.exec(select(GLAccount).limit(1)).first()
    )


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


@router.get("/api/companies")
def get_companies(session: Session = Depends(get_session)):
    return build_company_tree(session)


@router.get("/api/company-hierarchy")
def get_company_hierarchy(kind: HierarchyKind = HierarchyKind.BU, session: Session = Depends(get_session)):
    return build_company_hierarchy_tree(session, kind)


@router.get("/api/periods")
def get_periods(session: Session = Depends(get_session)):
    return build_period_tree(session)


@router.get("/api/gl")
def get_gl_master_tree(session: Session = Depends(get_session)):
    return build_gl_master_tree(session)


@router.get("/api/financial/tree")
def get_financial_tree(
    scope: str,
    year: Optional[int] = None,
    quarter: Optional[int] = Query(default=None, ge=1, le=4),
    month: Optional[int] = Query(default=None, ge=1, le=12),
    session: Session = Depends(get_session),
):
    if quarter is not None and month is not None:
        raise HTTPException(400, "quarter and month are mutually exclusive")
    if not _gl_seeded(session):
        raise HTTPException(500, "GL data not seeded — run `python backend/seed.py` first")

    resolved = _resolve_monetary_scope(session, scope)

    if resolved.get("notYetModelled"):
        return {"scope": scope, **_scope_meta(resolved), "notYetModelled": True, "nodes": {}}

    try:
        nodes = build_tree(session, resolved["companies"], year, quarter, month)
    except UnknownPeriod:
        raise HTTPException(404, f"Unknown period: year={year} quarter={quarter} month={month}")
    return {
        "scope": scope,
        **_scope_meta(resolved),
        "notYetModelled": False,
        "year": year,
        "quarter": quarter,
        "month": month,
        "nodes": nodes,
    }


@router.get("/api/financial/comparison")
def get_financial_comparison(
    scope: str,
    node: str,
    year_a: int = Query(alias="yearA"),
    quarter_a: Optional[int] = Query(default=None, alias="quarterA", ge=1, le=4),
    month_a: Optional[int] = Query(default=None, alias="monthA", ge=1, le=12),
    year_b: int = Query(alias="yearB"),
    quarter_b: Optional[int] = Query(default=None, alias="quarterB", ge=1, le=4),
    month_b: Optional[int] = Query(default=None, alias="monthB", ge=1, le=12),
    session: Session = Depends(get_session),
):
    if not _gl_seeded(session):
        raise HTTPException(500, "GL data not seeded — run `python backend/seed.py` first")

    resolved = _resolve_monetary_scope(session, scope)

    if resolved.get("notYetModelled"):
        return {"scope": scope, **_scope_meta(resolved), "notYetModelled": True, "nodes": {}}

    if _grain(quarter_a, month_a) != _grain(quarter_b, month_b):
        raise HTTPException(400, "periodA and periodB must be the same grain (both Month, both Quarter, or both Year)")

    try:
        tree_a = build_tree(session, resolved["companies"], year_a, quarter_a, month_a)
        tree_b = build_tree(session, resolved["companies"], year_b, quarter_b, month_b)
    except UnknownPeriod:
        raise HTTPException(404, "Unknown period")

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
        "yearA": year_a,
        "quarterA": quarter_a,
        "monthA": month_a,
        "yearB": year_b,
        "quarterB": quarter_b,
        "monthB": month_b,
        "nodes": diff_subtree(tree_a, tree_b, node),
    }


def _resolve_trailing_window(session: Session, trailing_end_year: int, trailing_end_month: int) -> list[tuple[int, int]]:
    """Resolves Trailing mode's window ending at `(trailing_end_year,
    trailing_end_month)` — shared by GET /api/vdt/tree and POST
    /api/vdt/trend-analysis (see docs/adr/0042, docs/adr/0051). Intersecting
    against `load_years()` is what produces a partial (< 12) window once the
    walk runs past the earliest seeded fiscal year — a deliberate, expected
    result (see the ADR's "no enforced minimum" decision), not an error.
    """
    known_years = set(load_years(session))
    if trailing_end_year not in known_years:
        raise HTTPException(404, f"Unknown fiscal year: {trailing_end_year}")
    candidates = trailing_periods(trailing_end_year, trailing_end_month, window_length=12)
    return [p for p in candidates if p[0] in known_years]


@router.get("/api/vdt/tree")
def get_vdt_tree(
    scope: str,
    year: Optional[int] = None,
    quarter: Optional[int] = Query(default=None, ge=1, le=4),
    month: Optional[int] = Query(default=None, ge=1, le=12),
    trailing_end_year: Optional[int] = Query(default=None, alias="trailingEndYear"),
    trailing_end_period: Optional[int] = Query(default=None, alias="trailingEndPeriod", ge=1, le=12),
    session: Session = Depends(get_session),
):
    """`year`/`quarter`/`month` is Financial Year mode, unchanged.
    `trailingEndYear`/`trailingEndPeriod` (a Month anchor) is Trailing mode —
    see docs/adr/0042, docs/adr/0051: the response's `months` field carries
    the resolved window (which can be shorter than 12 if the anchor is close
    to the earliest seeded data), so the frontend never has to re-derive it.
    The two are mutually exclusive in practice (the frontend never sends
    both), but `trailingEndYear` simply wins if it somehow did, since
    Trailing mode is the more specific request.
    """
    if quarter is not None and month is not None:
        raise HTTPException(400, "quarter and month are mutually exclusive")
    if not _gl_seeded(session):
        raise HTTPException(500, "GL data not seeded — run `python backend/seed.py` first")

    resolved = _resolve_monetary_scope(session, scope)

    if resolved.get("notYetModelled"):
        return {"scope": scope, **_scope_meta(resolved), "notYetModelled": True, "nodes": {}}

    if trailing_end_year is not None:
        if trailing_end_period is None:
            raise HTTPException(400, "trailingEndPeriod is required with trailingEndYear")
        window_periods = _resolve_trailing_window(session, trailing_end_year, trailing_end_period)
        nodes = build_vdt_tree(session, resolved["companies"], explicit_periods=window_periods)
        return {
            "scope": scope,
            **_scope_meta(resolved),
            "notYetModelled": False,
            "year": None,
            "quarter": None,
            "month": None,
            "months": [{"year": y, "period": p} for y, p in window_periods],
            "nodes": nodes,
        }

    try:
        nodes = build_vdt_tree(session, resolved["companies"], year, quarter, month)
    except UnknownPeriod:
        raise HTTPException(404, f"Unknown period: year={year} quarter={quarter} month={month}")
    return {
        "scope": scope,
        **_scope_meta(resolved),
        "notYetModelled": False,
        "year": year,
        "quarter": quarter,
        "month": month,
        "nodes": nodes,
    }


def _vdt_comparison_payload(
    session: Session,
    scope: str,
    node: str,
    year_a: int,
    quarter_a: Optional[int],
    month_a: Optional[int],
    year_b: int,
    quarter_b: Optional[int],
    month_b: Optional[int],
    ytd: bool,
) -> dict:
    """Shared by GET /api/vdt/comparison and POST /api/vdt/variance-analysis — both
    need the same resolved-scope, period-validated, diffed VDT subtree (see
    docs/adr/0034). Raises HTTPException on any resolution failure."""
    if not _gl_seeded(session):
        raise HTTPException(500, "GL data not seeded — run `python backend/seed.py` first")

    resolved = _resolve_monetary_scope(session, scope)

    if resolved.get("notYetModelled"):
        return {"scope": scope, **_scope_meta(resolved), "notYetModelled": True, "nodes": {}}

    if _grain(quarter_a, month_a) != _grain(quarter_b, month_b):
        raise HTTPException(400, "periodA and periodB must be the same grain (both Month, both Quarter, or both Year)")

    try:
        tree_a = build_vdt_tree(session, resolved["companies"], year_a, quarter_a, month_a, ytd=ytd)
        tree_b = build_vdt_tree(session, resolved["companies"], year_b, quarter_b, month_b, ytd=ytd)
    except UnknownPeriod:
        raise HTTPException(404, "Unknown period")

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
        "yearA": year_a,
        "quarterA": quarter_a,
        "monthA": month_a,
        "yearB": year_b,
        "quarterB": quarter_b,
        "monthB": month_b,
        "ytd": ytd,
        "nodes": diff_subtree(tree_a, tree_b, node),
    }


@router.get("/api/vdt/comparison")
def get_vdt_comparison(
    scope: str,
    node: str,
    year_a: int = Query(alias="yearA"),
    quarter_a: Optional[int] = Query(default=None, alias="quarterA", ge=1, le=4),
    month_a: Optional[int] = Query(default=None, alias="monthA", ge=1, le=12),
    year_b: int = Query(alias="yearB"),
    quarter_b: Optional[int] = Query(default=None, alias="quarterB", ge=1, le=4),
    month_b: Optional[int] = Query(default=None, alias="monthB", ge=1, le=12),
    ytd: bool = False,
    session: Session = Depends(get_session),
):
    return _vdt_comparison_payload(session, scope, node, year_a, quarter_a, month_a, year_b, quarter_b, month_b, ytd)


@router.post("/api/vdt/variance-analysis")
def post_vdt_variance_analysis(
    scope: str,
    node: str,
    year_a: int = Query(alias="yearA"),
    quarter_a: Optional[int] = Query(default=None, alias="quarterA", ge=1, le=4),
    month_a: Optional[int] = Query(default=None, alias="monthA", ge=1, le=12),
    year_b: int = Query(alias="yearB"),
    quarter_b: Optional[int] = Query(default=None, alias="quarterB", ge=1, le=4),
    month_b: Optional[int] = Query(default=None, alias="monthB", ge=1, le=12),
    ytd: bool = False,
    session: Session = Depends(get_session),
):
    payload = _vdt_comparison_payload(session, scope, node, year_a, quarter_a, month_a, year_b, quarter_b, month_b, ytd)
    if payload.get("notYetModelled"):
        raise HTTPException(404, "No VDT data modelled for the selected company yet")

    period_a_label = _period_label(session, year_a, quarter_a, month_a)
    period_b_label = _period_label(session, year_b, quarter_b, month_b)
    cache_key = (scope, node, year_a, quarter_a, month_a, year_b, quarter_b, month_b, ytd)
    try:
        variance_analysis = generate_variance_analysis(
            cache_key, node, payload["nodes"], period_a_label, period_b_label, currency=payload["currency"]
        )
    except VarianceAnalysisUnavailable as exc:
        raise HTTPException(503, str(exc))
    return {"varianceAnalysis": variance_analysis}


@router.post("/api/vdt/trend-analysis")
def post_vdt_trend_analysis(
    scope: str,
    year: Optional[int] = None,
    trailing_end_year: Optional[int] = Query(default=None, alias="trailingEndYear"),
    trailing_end_period: Optional[int] = Query(default=None, alias="trailingEndPeriod", ge=1, le=12),
    source: str = "actual",
    session: Session = Depends(get_session),
):
    """Whole-window MoM Trend Analysis narrative for VDT Trends — see
    docs/adr/0040, docs/adr/0042, docs/adr/0051. Always reads the fixed pilot
    anchor (SOC Crew Cost) and the underlying non-cumulative monthly series,
    regardless of the screen's Cumulative toggle — flagging needs monthly
    deltas, which a cumulative series would make meaningless. Exactly one of
    `year` (Financial Year mode) or `trailingEndYear`/`trailingEndPeriod`
    (Trailing mode, a Month anchor) must be given.
    """
    if source not in ("actual", "budget"):
        raise HTTPException(400, "source must be 'actual' or 'budget'")
    if (year is None) == (trailing_end_year is None):
        raise HTTPException(400, "exactly one of year or trailingEndYear must be provided")

    if not _gl_seeded(session):
        raise HTTPException(500, "GL data not seeded — run `python backend/seed.py` first")

    resolved = _resolve_monetary_scope(session, scope)
    if resolved.get("notYetModelled"):
        raise HTTPException(404, "No VDT data modelled for the selected company yet")

    periods = load_periods(session)

    if trailing_end_year is not None:
        if trailing_end_period is None:
            raise HTTPException(400, "trailingEndPeriod is required with trailingEndYear")
        window_periods = _resolve_trailing_window(session, trailing_end_year, trailing_end_period)
        tree = build_vdt_tree(session, resolved["companies"], explicit_periods=window_periods)
        month_labels = [calendar_month_label(periods[p], y) for y, p in window_periods]
        window_label = f"the trailing {len(window_periods)} months ending {month_labels[-1]}"
    else:
        if year not in set(load_years(session)):
            raise HTTPException(404, f"Unknown fiscal year: {year}")
        window_periods = periods_of_year(year)
        tree = build_vdt_tree(session, resolved["companies"], year)
        month_labels = [periods[p].label[:3] for _, p in window_periods]
        window_label = f"fiscal year {year}"

    # Keyed on the resolved window, not the request's own year/trailingEnd
    # identifier — a Financial Year request and a Trailing request that
    # happen to resolve to the same months share one cache entry (see
    # docs/adr/0042).
    cache_key = (scope, tuple(window_periods), source)

    if VDT_TRENDS_ANCHOR not in tree:
        raise HTTPException(404, f"Anchor {VDT_TRENDS_ANCHOR} missing from VDT tree")

    try:
        result = generate_trend_analysis(cache_key, tree, VDT_TRENDS_ANCHOR, source, window_label, month_labels)
    except TrendAnalysisUnavailable as exc:
        raise HTTPException(503, str(exc))
    return {"trendAnalysis": result}


@router.get("/api/vdt/reconciliation")
def get_vdt_reconciliation(
    scope: str,
    node: str,
    year: Optional[int] = None,
    quarter: Optional[int] = Query(default=None, ge=1, le=4),
    month: Optional[int] = Query(default=None, ge=1, le=12),
    ytd: bool = False,
    session: Session = Depends(get_session),
):
    """VDT-hierarchy subtree at `node`, plus the Accounting nodes needed to
    show each VDT Account leaf's FA GL anchor alongside it — see
    docs/adr/0033, docs/adr/0037. `node` anchors in the VDT tree (it's
    routinely a VDT-only VDT Hierarchy Node, e.g. SOC Crew Cost, with no same-code
    Accounting node at all), so `accounting.nodes` is not a subtree of the
    same code — it's just the specific anchor nodes the VDT subtree's leaves
    point to, keyed by their own GL code. No delta/polarity coloring: the two
    hierarchies are independent estimates that aren't required to reconcile —
    the gap between them is the point, not something to score.
    """
    if not _gl_seeded(session):
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
        accounting_tree = build_tree(session, resolved["companies"], year, quarter, month, ytd=ytd)
        vdt_tree = build_vdt_tree(session, resolved["companies"], year, quarter, month, ytd=ytd)
    except UnknownPeriod:
        raise HTTPException(404, f"Unknown period: year={year} quarter={quarter} month={month}")

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
        if n["nodeType"] == "VDT Account" and n.get("faGlCode")
    }
    accounting_nodes = {code: accounting_tree[code] for code in anchor_codes if code in accounting_tree}

    return {
        "scope": scope,
        **_scope_meta(resolved),
        "notYetModelled": False,
        "node": node,
        "year": year,
        "quarter": quarter,
        "month": month,
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
    source: str = "actual"  # 'actual' | 'budget'
    year: Optional[int] = None  # Financial Year mode
    trailingEndYear: Optional[int] = None  # Trailing mode (anchor Month year)
    trailingEndPeriod: Optional[int] = None  # Trailing mode (anchor Month, 1-12)


@router.post("/api/vdt/sensitivity")
def post_vdt_sensitivity(payload: SensitivityRequest, request: Request, session: Session = Depends(get_session)):
    """VDT Sensitivity Analysis — see docs/adr/0043. First streaming-response
    endpoint in this codebase: validation happens as ordinary HTTP errors
    before the SSE stream ever opens (so a client never has to parse an error
    out of an event frame), then the elasticity run streams `progress` events
    followed by exactly one `result` event.
    """
    if not (1.0 <= payload.bumpPct <= 20.0):
        raise HTTPException(422, "bump percent must be between 1 and 20")
    if payload.source not in ("actual", "budget"):
        raise HTTPException(400, "source must be 'actual' or 'budget'")
    if (payload.year is None) == (payload.trailingEndYear is None):
        raise HTTPException(400, "exactly one of year or trailingEndYear must be provided")

    if not _gl_seeded(session):
        raise HTTPException(500, "GL data not seeded — run `python backend/seed.py` first")

    resolved = _resolve_monetary_scope(session, payload.scope)
    if resolved.get("notYetModelled"):
        raise HTTPException(404, "No VDT data modelled for the selected company yet")

    periods = load_periods(session)

    if payload.trailingEndYear is not None:
        if payload.trailingEndPeriod is None:
            raise HTTPException(400, "trailingEndPeriod is required with trailingEndYear")
        window_periods = _resolve_trailing_window(session, payload.trailingEndYear, payload.trailingEndPeriod)
        month_labels = [calendar_month_label(periods[p], y) for y, p in window_periods]
        window_label = f"trailing {len(window_periods)} months ending {month_labels[-1]}" if month_labels else "trailing window"
        vdt_nodes = build_vdt_tree(session, resolved["companies"], explicit_periods=window_periods)
    else:
        if payload.year not in set(load_years(session)):
            raise HTTPException(404, f"Unknown fiscal year: {payload.year}")
        window_periods = periods_of_year(payload.year)
        month_labels = [periods[p].label[:3] for _, p in window_periods]
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
    engine = DriverEngine(session, resolved["companies"], window_periods)
    candidates = terminal_driver_candidates(engine, payload.scopeNode, vdt_nodes)

    total = len(candidates) * 2
    if total > SENSITIVITY_MAX_CYCLES:
        raise HTTPException(422, f"sensitivity run too large: {total} cycles, cap {SENSITIVITY_MAX_CYCLES}")

    generator = compute_sensitivity(
        session, company, payload.source, window_periods, root_code, candidates, payload.bumpPct, engine, total
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
