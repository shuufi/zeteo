"""Tests for vdt_tree.build_vdt_tree() — see docs/adr/0033.

Covers the three load-bearing rules this session's design settled on:
  1. wholesale-replace at a GL attachment point (old GL children become
     unreachable, not unioned with the new VDT Hierarchy Nodes)
  2. a VDT Account is always Driver-Formula-driven (no raw
     fact fallback) — driven and undriven cases
  3. sign is derived from the FA GL anchor's normal_balance, not stored on
     the VDT Account itself
"""

from backend.accounting.tree import periods_of_year
from backend.calendar.periods import trailing_periods
from backend.models import DriverFact, Financial, Source, Year
from backend.vdt.tree import build_vdt_tree

from conftest import fixture_graph  # noqa: E402

SECOND_YEAR = 2025


def _seed_second_fiscal_year(session, codes: dict[str, str]) -> None:
    """Adds a sibling 2025 Year (after fixture_graph's 2024) with its own
    facts, deliberately using DIFFERENT values than 2024's (100 -> 200 for
    the plain GL leaf, 10/2 -> 20/3 for the driven account's Headcount/Base
    Rate) — so a cross-fiscal-year window test can prove real per-year
    values combine correctly rather than one year's facts silently
    overwriting or duplicating into the other's slots (see docs/adr/0042).
    The static Period (1-12) reference rows are shared across every fiscal
    Year (see docs/adr/0051) — only a new Year row is needed here."""
    session.add(Year(year=SECOND_YEAR))
    session.commit()

    facts = []
    driver_facts = []
    for month in range(1, 13):
        facts.append(Financial(code=codes["gl_leaf_rev"], company=codes["company"], year=SECOND_YEAR, period=month, source=Source.ACTUAL, amount=200.0))
        driver_facts.append(
            DriverFact(code=codes["driver_headcount"], company=codes["company"], year=SECOND_YEAR, period=month, source=Source.ACTUAL, amount=20.0)
        )
        driver_facts.append(
            DriverFact(code=codes["driver_base_rate"], company=codes["company"], year=SECOND_YEAR, period=month, source=Source.ACTUAL, amount=3.0)
        )
    session.add_all(facts)
    session.add_all(driver_facts)
    session.commit()


def test_wholesale_replace_at_gl_attachment_point(session):
    codes = fixture_graph(session)
    tree = build_vdt_tree(session, [codes["company"]])

    # COR's VDT-side children are ONLY the VDT Hierarchy Node(s) attached there.
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
    tree = build_vdt_tree(session, [codes["company"]])

    rev_leaf = tree[codes["gl_leaf_rev"]]
    assert rev_leaf["actual"] == 1200.0
    assert rev_leaf["budget"] == 1080.0
    assert tree[codes["rev"]]["actual"] == 1200.0


def test_driven_vdt_account_computes_via_formula(session):
    codes = fixture_graph(session)
    tree = build_vdt_tree(session, [codes["company"]])

    # Headcount(10) x Rate(2, itself Formula-driven from BaseRate) = 20/month,
    # anchor GL is DEBIT -> sign flips negative -> 20 * 12 * -1 = -240.
    va1 = tree[codes["va_driven"]]
    assert va1["actual"] == -240.0
    assert va1["budget"] == -240.0
    assert va1["nodeType"] == "VDT Account"
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


def test_undriven_vdt_account_falls_back_to_zero(session):
    codes = fixture_graph(session)
    tree = build_vdt_tree(session, [codes["company"]])

    va2 = tree[codes["va_undriven"]]
    assert va2["actual"] == 0.0
    assert va2["budget"] == 0.0


def test_rollup_through_vdt_hierarchy_nodes(session):
    codes = fixture_graph(session)
    tree = build_vdt_tree(session, [codes["company"]])

    assert tree[codes["act_sub"]]["actual"] == -240.0  # va_driven + va_undriven
    assert tree[codes["act_top"]]["actual"] == -240.0
    assert tree[codes["cor"]]["actual"] == -240.0

    root = tree[codes["root"]]
    assert root["actual"] == 960.0  # 1200 (Revenue, unaffected) - 240 (VDT Cost of Revenue)
    assert root["budget"] == 840.0


def test_explicit_periods_param_matches_equivalent_year_derived_tree(session):
    """Trailing mode's explicit_periods path (docs/adr/0042, docs/adr/0051)
    must compute exactly the same figures as the Financial Year path when
    given the same 12 months in the same order — the generalization from a
    single year to an explicit (year, month) list must be behavior-preserving.
    """
    codes = fixture_graph(session)
    all_periods = periods_of_year(codes["year"])

    year_tree = build_vdt_tree(session, [codes["company"]], codes["year"])
    window_tree = build_vdt_tree(session, [codes["company"]], explicit_periods=all_periods)

    for node_id in (codes["rev"], codes["cor"], codes["act_top"], codes["va_driven"], codes["root"]):
        assert window_tree[node_id]["actual"] == year_tree[node_id]["actual"], node_id
        assert window_tree[node_id]["budget"] == year_tree[node_id]["budget"], node_id
        assert window_tree[node_id]["monthlyActual"] == year_tree[node_id]["monthlyActual"], node_id


def test_explicit_periods_param_supports_partial_window(session):
    """A Trailing-mode window shorter than 12 months (docs/adr/0042's "no
    enforced minimum" decision) must scale sums and Driver Formula evaluation
    to its own width, not silently assume 12."""
    codes = fixture_graph(session)
    first_six_periods = periods_of_year(codes["year"])[:6]

    tree = build_vdt_tree(session, [codes["company"]], explicit_periods=first_six_periods)

    assert len(tree[codes["rev"]]["monthlyActual"]) == 6
    assert tree[codes["gl_leaf_rev"]]["actual"] == 600.0  # 100/month * 6, not 12

    # va_driven: Headcount(10) x Rate(2) = 20/month, 6 months, DEBIT anchor flips sign.
    assert tree[codes["va_driven"]]["actual"] == -120.0
    assert len(tree[codes["va_driven"]]["monthlyActual"]) == 6


def test_explicit_periods_param_crosses_real_fiscal_year_boundary(session):
    """The manual/live check this session ran against the real seeded DB
    (curl against a 3-fiscal-year dataset) as an automated regression test:
    two ACTUALLY SEEDED fiscal years with DIFFERENT fact values, a window
    resolved by trailing_periods() that crosses their boundary, and
    assertions that both halves' distinct values land in the right slots —
    proving Financial/DriverFact loading and DriverEngine evaluation don't
    silently misalign or duplicate across the two Year rows (see
    docs/adr/0042). fixture_graph() alone only ever seeds one fiscal year
    (2024), so nothing else in this suite exercises a real cross-year fact
    load."""
    codes = fixture_graph(session)
    _seed_second_fiscal_year(session, codes)

    # 12 months ending 2025-06: 2024-07..2024-12 (fixture_graph's values)
    # then 2025-01..2025-06 (this test's different values).
    window = trailing_periods(SECOND_YEAR, 6, window_length=12)
    assert window == [(codes["year"], i) for i in range(7, 13)] + [(SECOND_YEAR, i) for i in range(1, 7)]

    tree = build_vdt_tree(session, [codes["company"]], explicit_periods=window)

    # Plain GL passthrough leaf: 6 months @ 100 (2024) + 6 months @ 200 (2025).
    assert tree[codes["gl_leaf_rev"]]["monthlyActual"] == [100.0] * 6 + [200.0] * 6
    assert tree[codes["gl_leaf_rev"]]["actual"] == 1800.0

    # Driver-Formula-driven account: Headcount x Base Rate, DEBIT anchor flips
    # sign. 2024 half: 10 x 2 = 20/month x 6 = 120. 2025 half (different
    # driver values): 20 x 3 = 60/month x 6 = 360. Wrong indexing (e.g. 2025's
    # facts overwriting 2024's slots, or vice versa) would produce -720 or
    # -240 instead of the correct mixed total.
    assert tree[codes["va_driven"]]["actual"] == -480.0
    assert tree[codes["va_driven"]]["monthlyActual"] == [-20.0] * 6 + [-60.0] * 6
