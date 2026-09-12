"""Year/Period fiscal calendar helpers — see docs/adr/0051.

Period is fiscal-relative (1-12, period 1 = a fiscal year's first month);
Quarter is derived arithmetic, never stored per-year. Replaces the old
adjacency-list Year->Quarter->Month walk (docs/adr/0025) now that Year and
Period are both plain integers rather than string codes threaded through a
parent-chain hierarchy.
"""

from typing import Optional

from sqlmodel import Session, select

from backend.calendar.models import Period, Year


class UnknownPeriod(Exception):
    pass


def quarter_of(period: int) -> int:
    return (period - 1) // 3 + 1


def load_years(session: Session) -> list[int]:
    return sorted(y.year for y in session.exec(select(Year)).all())


def load_periods(session: Session) -> dict[int, Period]:
    return {p.period: p for p in session.exec(select(Period)).all()}


def month_indices_for(month: Optional[int] = None, quarter: Optional[int] = None) -> Optional[set[int]]:
    """Which of a fiscal year's 12 monthly-array slots (0-based) a
    month/quarter/whole-year selection covers.

    None means "the whole year" — either no `month`/`quarter` was requested,
    or the selection is the Year itself — callers treat that as "sum
    everything". At most one of `month`/`quarter` may be given.
    """
    if month is not None:
        if not (1 <= month <= 12):
            raise UnknownPeriod(month)
        return {month - 1}
    if quarter is not None:
        if not (1 <= quarter <= 4):
            raise UnknownPeriod(quarter)
        start = (quarter - 1) * 3
        return {start, start + 1, start + 2}
    return None


def ytd_month_indices_for(month: Optional[int] = None, quarter: Optional[int] = None) -> Optional[set[int]]:
    """Cumulative fiscal-year-start-through-selection coverage, for YTD
    scoping (see docs/adr/0034, docs/adr/0037). A Quarter's last covered month
    is simply `quarter * 3`. A whole-year selection already covers every
    month, so it's unaffected by YTD — None, same as non-YTD.
    """
    if month is not None:
        if not (1 <= month <= 12):
            raise UnknownPeriod(month)
        return set(range(month))
    if quarter is not None:
        if not (1 <= quarter <= 4):
            raise UnknownPeriod(quarter)
        return set(range(quarter * 3))
    return None


def trailing_periods(anchor_year: int, anchor_month: int, window_length: int = 12) -> list[tuple[int, int]]:
    """Up to `window_length` (year, month) pairs ending at (and including)
    `(anchor_year, anchor_month)`, walking backward across fiscal-year
    boundaries — the VDT Trends Trailing mode window (see docs/adr/0042).
    Chronological (oldest first) order.

    Returns fewer than `window_length` pairs only if the caller keeps walking
    past the earliest year it cares about — this function itself never stops
    early; callers intersect the result against `load_years()` to produce a
    partial window when history runs out (a deliberate, expected result, not
    an error — see the ADR's "no enforced minimum" decision).
    """
    result: list[tuple[int, int]] = []
    year, month = anchor_year, anchor_month
    for _ in range(window_length):
        result.append((year, month))
        month -= 1
        if month < 1:
            year -= 1
            month = 12
    result.reverse()
    return result


def calendar_month_label(period_row: Period, year: int) -> str:
    """A Month's label reformatted calendar-style, e.g. label "September" +
    year 2025 -> "Sep '25" — used by Trailing mode's column headers, where the
    plain fiscal-year-qualified label ("Sep FY25") would be needlessly verbose
    next to Financial Year mode's bare month names, and a bare month name
    alone would be ambiguous once a window can repeat a month name across two
    fiscal years (see docs/adr/0042). Fiscal years are calendar-aligned today
    (period 1 = January — see seed.py), so this is a pure reformat, not a real
    calendar conversion.
    """
    return f"{period_row.label[:3]} '{year % 100:02d}"


def build_period_tree(session: Session) -> dict[str, dict]:
    """Year -> Quarter -> Month tree for the Context Bar picker. Computed by
    joining `Year` x `Period` (grouped by `quarter`) on every request — nothing
    here is stored as a hierarchy anymore (see docs/adr/0051). Node `id`s are
    synthetic UI keys only; `year`/`quarter`/`period` are the real identity
    the frontend should read.
    """
    years = load_years(session)
    periods = sorted(load_periods(session).values(), key=lambda p: p.period)

    def fy_label(year: int) -> str:
        return f"FY{year % 100:02d}"

    tree: dict[str, dict] = {}
    for year in years:
        year_id = str(year)
        quarter_ids = [f"{year}-Q{q}" for q in range(1, 5)]
        tree[year_id] = {
            "id": year_id,
            "label": fy_label(year),
            "periodType": "Year",
            "parentId": None,
            "childIds": quarter_ids,
            "year": year,
            # Convenience sort key for picker UIs — years already sort
            # correctly by their own int value, no separate sequence needed.
            "order": year,
        }
        for q in range(1, 5):
            q_id = f"{year}-Q{q}"
            month_ids = [f"{year}-M{p.period:02d}" for p in periods if p.quarter == q]
            tree[q_id] = {
                "id": q_id,
                "label": f"Q{q} {fy_label(year)}",
                "periodType": "Quarter",
                "parentId": year_id,
                "childIds": month_ids,
                "year": year,
                "quarter": q,
                "order": q,
            }
        for p in periods:
            m_id = f"{year}-M{p.period:02d}"
            tree[m_id] = {
                "id": m_id,
                "label": f"{p.label[:3]} {fy_label(year)}",
                "periodType": "Month",
                "parentId": f"{year}-Q{p.quarter}",
                "childIds": [],
                "year": year,
                "period": p.period,
                "order": p.period,
            }
    return tree
