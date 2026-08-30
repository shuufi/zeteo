"""MISC Group / Business Unit / Company hierarchy — see docs/adr/0028.

Mirrors periods.py's adjacency-list-walk shape, but for the business/company
dimension: MISC Group (root) -> Business Unit -> Company (leaf, the only
level ever referenced by gl_fact.company).
"""

from collections import defaultdict

from sqlmodel import Session, select

from models import CompanyNode, CompanyNodeType


class UnknownScope(Exception):
    pass


def load_company_hierarchy(session: Session) -> tuple[dict[str, CompanyNode], dict[str, list[str]]]:
    nodes = session.exec(select(CompanyNode)).all()
    node_by_code = {n.code: n for n in nodes}
    children_by_parent: dict[str, list[str]] = defaultdict(list)
    for n in nodes:
        if n.parent_code:
            children_by_parent[n.parent_code].append(n.code)
    return node_by_code, children_by_parent


def build_company_tree(session: Session) -> dict[str, dict]:
    node_by_code, children_by_parent = load_company_hierarchy(session)
    return {
        code: {
            "id": code,
            "label": node.label,
            "companyType": node.node_type.value,
            "parentId": node.parent_code,
            "childIds": sorted(children_by_parent.get(code, []), key=lambda c: node_by_code[c].order),
        }
        for code, node in node_by_code.items()
    }


def resolve_scope(session: Session, scope: str) -> dict:
    """Returns which sampled companies a scope (Group/BU/Company code) covers, and whether that's partial."""
    node_by_code, children_by_parent = load_company_hierarchy(session)
    node = node_by_code.get(scope)
    if node is None:
        raise UnknownScope(scope)

    def collect_companies(code: str) -> list[CompanyNode]:
        n = node_by_code[code]
        if n.node_type == CompanyNodeType.COMPANY:
            return [n]
        result: list[CompanyNode] = []
        for child in children_by_parent.get(code, []):
            result.extend(collect_companies(child))
        return result

    if node.node_type == CompanyNodeType.COMPANY:
        if not node.is_sampled:
            return {"kind": "company", "companies": [], "notYetModelled": True}
        return {"kind": "company", "companies": [node.code], "notYetModelled": False, "partial": False}

    descendants = collect_companies(scope)
    sampled = [c.code for c in descendants if c.is_sampled]
    kind = "group" if node.node_type == CompanyNodeType.GROUP else "bu"
    return {
        "kind": kind,
        "companies": sampled,
        "notYetModelled": False,
        "partial": len(sampled) < len(descendants),
        "sampledCompanyCount": len(sampled),
        "totalCompanyCount": len(descendants),
    }
