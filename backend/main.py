from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query
from sqlmodel import Session, select

load_dotenv()

from company_tree import InvalidMonetaryScope, MissingCompanyCurrency, UnknownScope, build_company_tree, resolve_scope
from db import get_session
from gl_tree import build_tree, diff_subtree, subtree
from models import GLNode
from narration import NarrationUnavailable, generate_narration
from periods import UnknownPeriod, build_period_tree, load_period_hierarchy
from vdt_tree import build_vdt_tree

VDT_COMPARISON_ROOT_TYPES = ("Reporting Root", "Reporting Node", "Activity Node")

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


@app.get("/api/vdt/tree")
def get_vdt_tree(scope: str, period: Optional[str] = None, session: Session = Depends(get_session)):
    if not session.exec(select(GLNode).limit(1)).first():
        raise HTTPException(500, "GL data not seeded — run `python backend/seed.py` first")

    resolved = _resolve_monetary_scope(session, scope)

    if resolved.get("notYetModelled"):
        return {"scope": scope, **_scope_meta(resolved), "notYetModelled": True, "nodes": {}}

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
    """Shared by GET /api/vdt/comparison and POST /api/vdt/narration — both
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


@app.post("/api/vdt/narration")
def post_vdt_narration(
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
        narration = generate_narration(cache_key, node, payload["nodes"], period_a, period_b)
    except NarrationUnavailable as exc:
        raise HTTPException(503, str(exc))
    return {"narration": narration}


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
