from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlmodel import Session, select

from company_tree import UnknownScope, build_company_tree, resolve_scope
from db import get_session
from gl_tree import build_tree, diff_subtree
from models import GLNode
from periods import UnknownPeriod, build_period_tree, load_period_hierarchy

app = FastAPI(title="Zeteo API")


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

    try:
        resolved = resolve_scope(session, scope)
    except UnknownScope:
        raise HTTPException(404, f"Unknown scope: {scope}")

    if resolved.get("notYetModelled"):
        return {"scope": scope, "notYetModelled": True, "nodes": {}}

    try:
        nodes = build_tree(session, resolved["companies"], period)
    except UnknownPeriod:
        raise HTTPException(404, f"Unknown period: {period}")
    return {
        "scope": scope,
        "scopeKind": resolved["kind"],
        "partial": resolved.get("partial", False),
        "sampledCompanyCount": resolved.get("sampledCompanyCount", len(resolved["companies"])),
        "totalCompanyCount": resolved.get("totalCompanyCount", 1),
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

    try:
        resolved = resolve_scope(session, scope)
    except UnknownScope:
        raise HTTPException(404, f"Unknown scope: {scope}")

    if resolved.get("notYetModelled"):
        return {"scope": scope, "notYetModelled": True, "nodes": {}}

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
        "scopeKind": resolved["kind"],
        "partial": resolved.get("partial", False),
        "sampledCompanyCount": resolved.get("sampledCompanyCount", len(resolved["companies"])),
        "totalCompanyCount": resolved.get("totalCompanyCount", 1),
        "notYetModelled": False,
        "node": node,
        "periodA": period_a,
        "periodB": period_b,
        "nodes": diff_subtree(tree_a, tree_b, node),
    }
