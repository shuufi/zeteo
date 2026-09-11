"""Coverage for company_tree.py's post-docs/adr/0045 split: company_tree.build_company_tree()
returns leaf-only Company master data, build_company_hierarchy_tree() returns the
BU grouping hierarchy with Company leaves merged in.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from company_tree import build_company_hierarchy_tree, build_company_tree  # noqa: E402
from models import HierarchyKind  # noqa: E402

from conftest import fixture_graph  # noqa: E402


def test_company_tree_is_leaf_only_no_hierarchy_fields(session):
    codes = fixture_graph(session)
    tree = build_company_tree(session)

    company = tree[codes["company"]]
    assert company["id"] == codes["company"]
    assert company["label"] == "Company One"
    assert company["currency"] == "MYR"
    assert company["isSampled"] is True
    assert company["buNodeCode"] == codes["business_unit"]
    assert "parentId" not in company and "childIds" not in company

    # Group/BU rows never appear here — they live only in company_hierarchy now.
    assert codes["group"] not in tree
    assert codes["business_unit"] not in tree


def test_company_hierarchy_tree_merges_company_leaves_under_bu_node(session):
    codes = fixture_graph(session)
    tree = build_company_hierarchy_tree(session, HierarchyKind.BU)

    root = tree[codes["group"]]
    assert root["parentId"] is None
    assert root["childIds"] == [codes["business_unit"]]
    assert root["kind"] == "BU"
    assert root["isCompany"] is False

    bu = tree[codes["business_unit"]]
    assert bu["parentId"] == codes["group"]
    assert bu["childIds"] == [codes["company"]]
    assert bu["isCompany"] is False

    company_leaf = tree[codes["company"]]
    assert company_leaf["parentId"] == codes["business_unit"]
    assert company_leaf["childIds"] == []
    assert company_leaf["label"] == "Company One"
    assert company_leaf["isCompany"] is True
