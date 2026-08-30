from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from sqlmodel import Session, select

from company_tree import UnknownScope, build_company_tree, resolve_scope
from db import get_session
from gl_tree import build_tree
from models import GLNode
from periods import UnknownPeriod, build_period_tree

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
