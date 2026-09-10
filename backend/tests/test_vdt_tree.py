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

from models import DriverFact, GLFact, Period, PeriodType, Source  # noqa: E402
from periods import load_period_hierarchy, ordered_month_codes_of_year, trailing_month_codes  # noqa: E402
from vdt_tree import build_vdt_tree  # noqa: E402

from conftest import MONTH_LABELS, fixture_graph  # noqa: E402

SECOND_YEAR = "FY25"


def _seed_second_fiscal_year(session, codes: dict[str, str]) -> None:
    """Adds a sibling FY25 Year (order=2, after fixture_graph's FY24) with
    its own facts, deliberately using DIFFERENT values than FY24's (100 ->
    200 for the plain GL leaf, 10/2 -> 20/3 for the driven account's
    Headcount/Base Rate) — so a cross-fiscal-year window test can prove real
    per-year values combine correctly rather than one year's facts silently
    overwriting or duplicating into the other's slots (see docs/adr/0042)."""
    periods = [Period(code=SECOND_YEAR, label=SECOND_YEAR, parent_code=None, period_type=PeriodType.YEAR, order=2)]
    month = 1
    for quarter in range(1, 5):
        quarter_code = f"{SECOND_YEAR}-Q{quarter}"
        periods.append(
            Period(code=quarter_code, label=f"Q{quarter} {SECOND_YEAR}", parent_code=SECOND_YEAR, period_type=PeriodType.QUARTER, order=quarter)
        )
        for _ in range(3):
            month_code = f"{SECOND_YEAR}-M{month:02d}"
            periods.append(
                Period(
                    code=month_code,
                    label=f"{MONTH_LABELS[month - 1]} {SECOND_YEAR}",
                    parent_code=quarter_code,
                    period_type=PeriodType.MONTH,
                    order=month,
                )
            )
            month += 1
    session.add_all(periods)
    session.commit()

    facts = []
    driver_facts = []
    for month in range(1, 13):
        period_code = f"{SECOND_YEAR}-M{month:02d}"
        facts.append(GLFact(code=codes["gl_leaf_rev"], company=codes["company"], period_code=period_code, source=Source.ACTUAL, amount=200.0))
        driver_facts.append(
            DriverFact(code=codes["driver_headcount"], company=codes["company"], period_code=period_code, source=Source.ACTUAL, amount=20.0)
        )
        driver_facts.append(
            DriverFact(code=codes["driver_base_rate"], company=codes["company"], period_code=period_code, source=Source.ACTUAL, amount=3.0)
        )
    session.add_all(facts)
    session.add_all(driver_facts)
    session.commit()


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


def test_month_codes_param_matches_equivalent_year_derived_tree(session):
    """Trailing mode's month_codes path (docs/adr/0042) must compute exactly
    the same figures as the Financial Year path when given the same 12
    months in the same order — the generalization from a single year_code to
    an explicit month-code list must be behavior-preserving."""
    codes = fixture_graph(session)
    period_by_code, period_children = load_period_hierarchy(session)
    all_months = ordered_month_codes_of_year(period_by_code, period_children, codes["year"])

    year_tree = build_vdt_tree(session, [codes["company"]], codes["year"])
    window_tree = build_vdt_tree(session, [codes["company"]], month_codes=all_months)

    for node_id in (codes["rev"], codes["cor"], codes["act_top"], codes["va_driven"], codes["root"]):
        assert window_tree[node_id]["actual"] == year_tree[node_id]["actual"], node_id
        assert window_tree[node_id]["budget"] == year_tree[node_id]["budget"], node_id
        assert window_tree[node_id]["monthlyActual"] == year_tree[node_id]["monthlyActual"], node_id


def test_month_codes_param_supports_partial_window(session):
    """A Trailing-mode window shorter than 12 months (docs/adr/0042's "no
    enforced minimum" decision) must scale sums and Driver Formula evaluation
    to its own width, not silently assume 12."""
    codes = fixture_graph(session)
    period_by_code, period_children = load_period_hierarchy(session)
    first_six_months = ordered_month_codes_of_year(period_by_code, period_children, codes["year"])[:6]

    tree = build_vdt_tree(session, [codes["company"]], month_codes=first_six_months)

    assert len(tree[codes["rev"]]["monthlyActual"]) == 6
    assert tree[codes["gl_leaf_rev"]]["actual"] == 600.0  # 100/month * 6, not 12

    # va_driven: Headcount(10) x Rate(2) = 20/month, 6 months, DEBIT anchor flips sign.
    assert tree[codes["va_driven"]]["actual"] == -120.0
    assert len(tree[codes["va_driven"]]["monthlyActual"]) == 6


def test_month_codes_param_crosses_real_fiscal_year_boundary(session):
    """The manual/live check this session ran against the real seeded DB
    (curl against a 3-fiscal-year dataset) as an automated regression test:
    two ACTUALLY SEEDED fiscal years with DIFFERENT fact values, a window
    resolved by trailing_month_codes() that crosses their boundary, and
    assertions that both halves' distinct values land in the right slots —
    proving GLFact/DriverFact loading and DriverEngine evaluation don't
    silently misalign or duplicate across the two Year rows (see
    docs/adr/0042). fixture_graph() alone only ever seeds one fiscal year
    (FY24), so nothing else in this suite exercises a real cross-year fact
    load."""
    codes = fixture_graph(session)
    _seed_second_fiscal_year(session, codes)
    period_by_code, period_children = load_period_hierarchy(session)

    # 12 months ending FY25-M06: FY24-M07..FY24-M12 (fixture_graph's values)
    # then FY25-M01..FY25-M06 (this test's different values).
    window = trailing_month_codes(period_by_code, period_children, f"{SECOND_YEAR}-M06")
    assert window == [f"{codes['year']}-M{i:02d}" for i in range(7, 13)] + [f"{SECOND_YEAR}-M{i:02d}" for i in range(1, 7)]

    tree = build_vdt_tree(session, [codes["company"]], month_codes=window)

    # Plain GL passthrough leaf: 6 months @ 100 (FY24) + 6 months @ 200 (FY25).
    assert tree[codes["gl_leaf_rev"]]["monthlyActual"] == [100.0] * 6 + [200.0] * 6
    assert tree[codes["gl_leaf_rev"]]["actual"] == 1800.0

    # Driver-Formula-driven account: Headcount x Base Rate, DEBIT anchor flips
    # sign. FY24 half: 10 x 2 = 20/month x 6 = 120. FY25 half (different
    # driver values): 20 x 3 = 60/month x 6 = 360. Wrong indexing (e.g. FY25's
    # facts overwriting FY24's slots, or vice versa) would produce -720 or
    # -240 instead of the correct mixed total.
    assert tree[codes["va_driven"]]["actual"] == -480.0
    assert tree[codes["va_driven"]]["monthlyActual"] == [-20.0] * 6 + [-60.0] * 6
