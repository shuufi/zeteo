"""Company master data and its BU/Legal grouping hierarchy — see docs/adr/0045.

`company` holds leaf Company rows only (see docs/adr/0028's superseded
Group/BU/Company shape). Grouping above Company lives in `company_hierarchy`,
one polymorphic self-referencing table per `hierarchy_kind` (BU today, Legal
planned) — mirrors gl_tree.py/periods.py's adjacency-list-walk shape, but
depth is unconstrained rather than a fixed number of tiers.
"""

from collections import defaultdict

from sqlmodel import Session, select

from models import CompanyHierarchy, CompanyNode, HierarchyKind


class UnknownScope(Exception):
    pass


class InvalidMonetaryScope(Exception):
    pass


class MissingCompanyCurrency(Exception):
    pass


def load_companies(session: Session) -> dict[str, CompanyNode]:
    return {c.code: c for c in session.exec(select(CompanyNode)).all()}


def load_company_hierarchy(
    session: Session, kind: HierarchyKind
) -> tuple[dict[str, CompanyHierarchy], dict[str, list[str]]]:
    nodes = session.exec(select(CompanyHierarchy).where(CompanyHierarchy.hierarchy_kind == kind)).all()
    node_by_code = {n.code: n for n in nodes}
    children_by_parent: dict[str, list[str]] = defaultdict(list)
    for n in nodes:
        if n.parent_code:
            children_by_parent[n.parent_code].append(n.code)
    return node_by_code, children_by_parent


def build_company_tree(session: Session) -> dict[str, dict]:
    """Company master data — leaves only, no hierarchy (see docs/adr/0045)."""
    companies = load_companies(session)
    return {
        code: {
            "id": code,
            "label": c.label,
            "currency": c.currency,
            "isSampled": c.is_sampled,
            "buNodeCode": c.bu_node_code,
        }
        for code, c in companies.items()
    }


def build_company_hierarchy_tree(session: Session, kind: HierarchyKind) -> dict[str, dict]:
    """The grouping hierarchy above Company (`kind`), with Company leaves
    merged in as childless nodes under their `bu_node_code` parent — one
    combined tree for the frontend to walk generically (see docs/adr/0045).
    """
    node_by_code, children_by_parent = load_company_hierarchy(session, kind)
    result: dict[str, dict] = {
        code: {
            "id": code,
            "label": node.label,
            "parentId": node.parent_code,
            "childIds": sorted(children_by_parent.get(code, []), key=lambda c: node_by_code[c].order),
            "kind": node.hierarchy_kind.value,
            "isCompany": False,
        }
        for code, node in node_by_code.items()
    }
    if kind == HierarchyKind.BU:
        for code, company in load_companies(session).items():
            result[code] = {
                "id": code,
                "label": company.label,
                "parentId": company.bu_node_code,
                "childIds": [],
                "kind": kind.value,
                "isCompany": True,
            }
            if company.bu_node_code in result:
                result[company.bu_node_code]["childIds"].append(code)
    return result


def resolve_scope(session: Session, scope: str) -> dict:
    """Resolve one Company monetary scope; Group/BU rollups require FX and are rejected."""
    node = load_companies(session).get(scope)
    if node is None:
        bu_node_by_code, _ = load_company_hierarchy(session, HierarchyKind.BU)
        if scope in bu_node_by_code:
            raise InvalidMonetaryScope(scope)
        raise UnknownScope(scope)
    if not node.currency:
        raise MissingCompanyCurrency(scope)
    return {
        "kind": "company",
        "companies": [node.code] if node.is_sampled else [],
        "currency": node.currency,
        "notYetModelled": not node.is_sampled,
    }
