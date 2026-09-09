"""Unit tests for periods.py's month-index scoping — see docs/adr/0037. Not
previously covered: month_indices_for/ytd_month_indices_for only ever got
exercised indirectly, and only ever with period_code=None or a Year period,
both of which short-circuit before reaching the Quarter/Month branches these
tests target directly.
"""

import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from conftest import fixture_graph  # noqa: E402
from models import Period, PeriodType  # noqa: E402
from periods import (  # noqa: E402
    UnknownPeriod,
    calendar_month_label,
    load_period_hierarchy,
    month_indices_for,
    ordered_month_codes_of_year,
    trailing_month_codes,
    ytd_month_indices_for,
)


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


MONTH_LABELS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _two_year_hierarchy() -> tuple[dict[str, Period], dict[str, list[str]]]:
    """FY24/FY25 sibling Year roots (see docs/adr/0032), built directly as
    plain dicts — no DB needed, since trailing_month_codes/
    ordered_month_codes_of_year/calendar_month_label are pure functions over
    these two structures."""
    period_by_code: dict[str, Period] = {}
    children_by_parent: dict[str, list[str]] = defaultdict(list)
    for year_order, fiscal_year in enumerate(["FY24", "FY25"], start=1):
        period_by_code[fiscal_year] = Period(
            code=fiscal_year, label=fiscal_year, parent_code=None, period_type=PeriodType.YEAR, order=year_order
        )
        month = 1
        for quarter in range(1, 5):
            quarter_code = f"{fiscal_year}-Q{quarter}"
            period_by_code[quarter_code] = Period(
                code=quarter_code, label=f"Q{quarter} {fiscal_year}", parent_code=fiscal_year, period_type=PeriodType.QUARTER, order=quarter
            )
            children_by_parent[fiscal_year].append(quarter_code)
            for _ in range(3):
                month_code = f"{fiscal_year}-M{month:02d}"
                period_by_code[month_code] = Period(
                    code=month_code,
                    label=f"{MONTH_LABELS[month - 1]} {fiscal_year}",
                    parent_code=quarter_code,
                    period_type=PeriodType.MONTH,
                    order=month,
                )
                children_by_parent[quarter_code].append(month_code)
                month += 1
    return period_by_code, children_by_parent


def test_trailing_month_codes_within_one_year():
    period_by_code, period_children = _two_year_hierarchy()
    assert trailing_month_codes(period_by_code, period_children, "FY24-M06") == [
        f"FY24-M{i:02d}" for i in range(1, 7)
    ]


def test_trailing_month_codes_crosses_fiscal_year_boundary():
    period_by_code, period_children = _two_year_hierarchy()
    # 12 months ending FY25-M03 (March of FY25) reaches back into FY24's
    # April..December — the whole point of Trailing mode (see docs/adr/0042).
    result = trailing_month_codes(period_by_code, period_children, "FY25-M03")
    assert result == [f"FY24-M{i:02d}" for i in range(4, 13)] + [f"FY25-M{i:02d}" for i in range(1, 4)]
    assert len(result) == 12


def test_trailing_month_codes_partial_window_at_start_of_history():
    period_by_code, period_children = _two_year_hierarchy()
    # Anchor at the very first seeded month — no history before it, so the
    # window is deliberately shorter than 12 (see the ADR's "no enforced
    # minimum" decision), not an error.
    assert trailing_month_codes(period_by_code, period_children, "FY24-M01") == ["FY24-M01"]
    assert trailing_month_codes(period_by_code, period_children, "FY24-M03") == ["FY24-M01", "FY24-M02", "FY24-M03"]


def test_trailing_month_codes_rejects_non_month_anchor():
    period_by_code, period_children = _two_year_hierarchy()
    try:
        trailing_month_codes(period_by_code, period_children, "FY24-Q2")
        assert False, "expected UnknownPeriod for a non-Month anchor"
    except UnknownPeriod:
        pass


def test_trailing_month_codes_rejects_unknown_anchor():
    period_by_code, period_children = _two_year_hierarchy()
    try:
        trailing_month_codes(period_by_code, period_children, "NOT-REAL")
        assert False, "expected UnknownPeriod for an unknown anchor"
    except UnknownPeriod:
        pass


def test_ordered_month_codes_of_year_is_chronological():
    period_by_code, period_children = _two_year_hierarchy()
    assert ordered_month_codes_of_year(period_by_code, period_children, "FY24") == [
        f"FY24-M{i:02d}" for i in range(1, 13)
    ]


def test_calendar_month_label_reformats_fiscal_label():
    period_by_code, _ = _two_year_hierarchy()
    assert calendar_month_label(period_by_code["FY25-M09"]) == "Sep '25"
    assert calendar_month_label(period_by_code["FY24-M01"]) == "Jan '24"
