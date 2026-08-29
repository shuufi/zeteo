import json
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from sqlmodel import Session, select

from db import get_session
from gl_tree import UnknownScope, build_tree, resolve_scope
from models import GLNode

app = FastAPI(title="Zeteo API")

COMPANIES_PATH = Path(__file__).parent / "data" / "companies.json"


@app.get("/api/companies")
def get_companies():
    return json.loads(COMPANIES_PATH.read_text(encoding="utf-8"))


@app.get("/api/gl/tree")
def get_gl_tree(scope: str, session: Session = Depends(get_session)):
    if not session.exec(select(GLNode).limit(1)).first():
        raise HTTPException(500, "GL data not seeded — run `python backend/seed.py` first")

    try:
        resolved = resolve_scope(scope)
    except UnknownScope:
        raise HTTPException(404, f"Unknown scope: {scope}")

    if resolved.get("notYetModelled"):
        return {"scope": scope, "notYetModelled": True, "nodes": {}}

    nodes = build_tree(session, resolved["companies"])
    return {
        "scope": scope,
        "scopeKind": resolved["kind"],
        "partial": resolved.get("partial", False),
        "sampledCompanyCount": resolved.get("sampledCompanyCount", len(resolved["companies"])),
        "totalCompanyCount": resolved.get("totalCompanyCount", 1),
        "notYetModelled": False,
        "nodes": nodes,
    }
