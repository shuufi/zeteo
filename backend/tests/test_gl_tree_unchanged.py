"""Regression guard for gl_tree.build_tree() — the Accounting hierarchy Trends
reads from (docs/adr/0033 rule 5: Trends must stay completely unaffected by
the VDT work). Asserts against hand-computed values on the fixture graph so a
future refactor of gl_tree.py's extracted helpers (compute_gl_leaf,
sum_children_entry, load_monthly, scoped_sum) can't silently change output.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from gl_tree import build_tree  # noqa: E402

from conftest import fixture_graph  # noqa: E402


def test_plain_passthrough_leaf_sign_and_sum(session):
    codes = fixture_graph(session)
    tree = build_tree(session, [codes["company"]], None)

    rev_leaf = tree[codes["gl_leaf_rev"]]
    assert rev_leaf["actual"] == 1200.0  # 100/month * 12, CREDIT -> positive
    assert rev_leaf["budget"] == 1080.0


def test_untouched_subtree_reachable_and_summed(session):
    codes = fixture_graph(session)
    tree = build_tree(session, [codes["company"]], None)

    old_leaf = tree[codes["gl_old_leaf"]]
    assert old_leaf["actual"] == -600.0  # 50/month * 12, DEBIT -> negative
    assert old_leaf["budget"] == -540.0

    anchor_leaf = tree[codes["gl_anchor_leaf"]]
    assert anchor_leaf["actual"] == -360.0
    assert anchor_leaf["budget"] == -336.0

    cor = tree[codes["cor"]]
    assert cor["actual"] == -960.0  # old_leaf + anchor_leaf
    assert cor["budget"] == -876.0
    assert set(cor["childIds"]) == {codes["gl_old_node"], codes["gl_anchor_leaf"]}


def test_root_rollup(session):
    codes = fixture_graph(session)
    tree = build_tree(session, [codes["company"]], None)

    root = tree[codes["root"]]
    assert root["actual"] == 240.0  # 1200 (Revenue) - 960 (Cost of Revenue)
    assert root["budget"] == 204.0


def test_activity_node_tables_do_not_appear_in_accounting_tree(session):
    codes = fixture_graph(session)
    tree = build_tree(session, [codes["company"]], None)

    assert codes["act_top"] not in tree
    assert codes["va_driven"] not in tree
