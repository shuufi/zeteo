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


class InvalidMonetaryScope(Exception):
    pass


class MissingCompanyCurrency(Exception):
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
            "currency": node.currency,
            "parentId": node.parent_code,
            "childIds": sorted(children_by_parent.get(code, []), key=lambda c: node_by_code[c].order),
        }
        for code, node in node_by_code.items()
    }


def resolve_scope(session: Session, scope: str) -> dict:
    """Resolve one Company monetary scope; Group/BU rollups require FX and are rejected."""
    node_by_code, _ = load_company_hierarchy(session)
    node = node_by_code.get(scope)
    if node is None:
        raise UnknownScope(scope)
    if node.node_type != CompanyNodeType.COMPANY:
        raise InvalidMonetaryScope(scope)
    if not node.currency:
        raise MissingCompanyCurrency(scope)
    return {
        "kind": "company",
        "companies": [node.code] if node.is_sampled else [],
        "currency": node.currency,
        "notYetModelled": not node.is_sampled,
    }
