"""Tests for vdt_tree.build_vdt_tree() — see docs/adr/0033.

Covers the three load-bearing rules this session's design settled on:
  1. wholesale-replace at a GL attachment point (old GL children become
     unreachable, not unioned with the new Activity Nodes)
  2. a Posting Activity Account is always Driver-Formula-driven (no raw
     fact fallback) — driven and undriven cases
  3. sign is derived from the FA GL anchor's normal_balance, not stored on
     the Posting Activity Account itself
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from vdt_tree import build_vdt_tree  # noqa: E402

from conftest import fixture_graph  # noqa: E402


def test_wholesale_replace_at_gl_attachment_point(session):
    codes = fixture_graph(session)
    tree = build_vdt_tree(session, [codes["company"]], None)

    # COR's VDT-side children are ONLY the Activity Node(s) attached there.
    assert tree[codes["cor"]]["childIds"] == [codes["act_top"]]

    # The old GL subtree hanging off COR-OLD is unreachable in this tree —
    # deliberately absent, not an error (see vdt_tree.py's module docstring).
    assert codes["gl_old_node"] not in tree
    assert codes["gl_old_leaf"] not in tree

    # The other sibling leaf that used to hang directly off COR is also
    # unreachable — wholesale replace, not a partial union.
    assert codes["gl_anchor_leaf"] not in tree


def test_unaffected_branches_pass_through_unmodified(session):
    codes = fixture_graph(session)
    tree = build_vdt_tree(session, [codes["company"]], None)

    rev_leaf = tree[codes["gl_leaf_rev"]]
    assert rev_leaf["actual"] == 1200.0
    assert rev_leaf["budget"] == 1080.0
    assert tree[codes["rev"]]["actual"] == 1200.0


def test_driven_posting_activity_account_computes_via_formula(session):
    codes = fixture_graph(session)
    tree = build_vdt_tree(session, [codes["company"]], None)

    # Headcount(10) x Rate(2, itself Formula-driven from BaseRate) = 20/month,
    # anchor GL is DEBIT -> sign flips negative -> 20 * 12 * -1 = -240.
    va1 = tree[codes["va_driven"]]
    assert va1["actual"] == -240.0
    assert va1["budget"] == -240.0
    assert va1["nodeType"] == "Posting Activity Account"
    assert va1["faGlCode"] == codes["gl_anchor_leaf"]

    # Driver Formula / Driver nodes spliced in under the driven account,
    # recursing one level (DRV-RATE is itself Formula-driven from BaseRate).
    formula_id = f"{codes['va_driven']}::{codes['formula_va1']}"
    assert formula_id in tree[codes["va_driven"]]["childIds"]
    assert formula_id in tree
    rate_driver_id = f"{formula_id}::{codes['driver_rate']}"
    assert rate_driver_id in tree
    nested_formula_id = f"{rate_driver_id}::{codes['formula_rate']}"
    assert nested_formula_id in tree


def test_undriven_posting_activity_account_falls_back_to_zero(session):
    codes = fixture_graph(session)
    tree = build_vdt_tree(session, [codes["company"]], None)

    va2 = tree[codes["va_undriven"]]
    assert va2["actual"] == 0.0
    assert va2["budget"] == 0.0


def test_rollup_through_activity_nodes(session):
    codes = fixture_graph(session)
    tree = build_vdt_tree(session, [codes["company"]], None)

    assert tree[codes["act_sub"]]["actual"] == -240.0  # va_driven + va_undriven
    assert tree[codes["act_top"]]["actual"] == -240.0
    assert tree[codes["cor"]]["actual"] == -240.0

    root = tree[codes["root"]]
    assert root["actual"] == 960.0  # 1200 (Revenue, unaffected) - 240 (VDT Cost of Revenue)
    assert root["budget"] == 840.0
