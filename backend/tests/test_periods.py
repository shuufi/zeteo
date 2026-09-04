"""Unit tests for periods.py's month-index scoping — see docs/adr/0037. Not
previously covered: month_indices_for/ytd_month_indices_for only ever got
exercised indirectly, and only ever with period_code=None or a Year period,
both of which short-circuit before reaching the Quarter/Month branches these
tests target directly.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from conftest import fixture_graph  # noqa: E402
from periods import load_period_hierarchy, month_indices_for, ytd_month_indices_for  # noqa: E402


def _hierarchy(session):
    fixture_graph(session)
    return load_period_hierarchy(session)


def test_month_indices_for_single_month(session):
    period_by_code, period_children = _hierarchy(session)
    assert month_indices_for(period_by_code, period_children, "FY24-M06") == {5}


def test_month_indices_for_quarter_is_its_own_three_months(session):
    period_by_code, period_children = _hierarchy(session)
    assert month_indices_for(period_by_code, period_children, "FY24-Q2") == {3, 4, 5}


def test_ytd_month_indices_for_month_is_cumulative(session):
    period_by_code, period_children = _hierarchy(session)
    assert ytd_month_indices_for(period_by_code, period_children, "FY24-M06") == {0, 1, 2, 3, 4, 5}


def test_ytd_month_indices_for_quarter_is_cumulative_through_quarter_end(session):
    period_by_code, period_children = _hierarchy(session)
    # Q2 YTD must match June's (its last month) YTD exactly.
    assert ytd_month_indices_for(period_by_code, period_children, "FY24-Q2") == {0, 1, 2, 3, 4, 5}
    assert ytd_month_indices_for(period_by_code, period_children, "FY24-Q2") == ytd_month_indices_for(
        period_by_code, period_children, "FY24-M06"
    )


def test_ytd_month_indices_for_q1_is_just_its_own_three_months(session):
    period_by_code, period_children = _hierarchy(session)
    assert ytd_month_indices_for(period_by_code, period_children, "FY24-Q1") == {0, 1, 2}


def test_ytd_month_indices_for_q4_is_whole_year(session):
    period_by_code, period_children = _hierarchy(session)
    assert ytd_month_indices_for(period_by_code, period_children, "FY24-Q4") == set(range(12))


def test_ytd_month_indices_for_year_is_none_like_non_ytd(session):
    period_by_code, period_children = _hierarchy(session)
    assert ytd_month_indices_for(period_by_code, period_children, "FY24") is None
    assert month_indices_for(period_by_code, period_children, "FY24") is None
