"""Unit tests for periods.py — see docs/adr/0037, docs/adr/0051."""

from conftest import build_periods, fixture_graph
from backend.calendar.periods import (
    calendar_month_label,
    load_periods,
    load_years,
    month_indices_for,
    quarter_of,
    trailing_periods,
    ytd_month_indices_for,
)


def test_quarter_of_derives_correct_quarter_for_every_month():
    assert [quarter_of(m) for m in range(1, 13)] == [1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4]


def test_month_indices_for_single_month():
    assert month_indices_for(month=6) == {5}


def test_month_indices_for_quarter_is_its_own_three_months():
    assert month_indices_for(quarter=2) == {3, 4, 5}


def test_month_indices_for_whole_year_is_none():
    assert month_indices_for() is None


def test_ytd_month_indices_for_month_is_cumulative():
    assert ytd_month_indices_for(month=6) == {0, 1, 2, 3, 4, 5}


def test_ytd_month_indices_for_quarter_is_cumulative_through_quarter_end():
    # Q2 YTD must match June's (its last month) YTD exactly.
    assert ytd_month_indices_for(quarter=2) == {0, 1, 2, 3, 4, 5}
    assert ytd_month_indices_for(quarter=2) == ytd_month_indices_for(month=6)


def test_ytd_month_indices_for_q1_is_just_its_own_three_months():
    assert ytd_month_indices_for(quarter=1) == {0, 1, 2}


def test_ytd_month_indices_for_q4_is_whole_year():
    assert ytd_month_indices_for(quarter=4) == set(range(12))


def test_ytd_month_indices_for_whole_year_is_none_like_non_ytd():
    assert ytd_month_indices_for() is None
    assert month_indices_for() is None


def test_trailing_periods_within_one_year():
    assert trailing_periods(2024, 6, window_length=6) == [(2024, i) for i in range(1, 7)]


def test_trailing_periods_crosses_fiscal_year_boundary():
    # 12 pairs ending (2025, 3) reaches back into 2024's April..December —
    # the whole point of Trailing mode (see docs/adr/0042).
    result = trailing_periods(2025, 3, window_length=12)
    assert result == [(2024, i) for i in range(4, 13)] + [(2025, i) for i in range(1, 4)]
    assert len(result) == 12


def test_trailing_periods_walks_arithmetic_past_any_year_existence_check():
    # trailing_periods is pure month/year arithmetic — it has no concept of
    # which fiscal years are actually seeded; callers intersect against
    # load_years() themselves to produce a partial window (see
    # _resolve_trailing_window in api/routes.py and its endpoint tests).
    assert trailing_periods(2024, 1, window_length=3) == [(2023, 11), (2023, 12), (2024, 1)]


def test_calendar_month_label_reformats_month_and_year():
    periods = {p.period: p for p in build_periods()}
    assert calendar_month_label(periods[9], 2025) == "Sep '25"
    assert calendar_month_label(periods[1], 2024) == "Jan '24"


def test_load_years_and_load_periods(session):
    codes = fixture_graph(session)
    assert load_years(session) == [codes["year"]]
    periods = load_periods(session)
    assert set(periods.keys()) == set(range(1, 13))
    assert periods[1].label == "January"
    assert periods[1].quarter == 1
    assert periods[12].quarter == 4
