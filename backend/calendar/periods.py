"""Year/Quarter/Month period hierarchy — see docs/adr/0025 and docs/adr/0032.

Mirrors gl_tree.py's adjacency-list-walk shape, but for the much smaller
period dimension (17 rows per fiscal year: 1 Year + 4 Quarters + 12 Months —
multiple fiscal years coexist as sibling Year roots, not one shared tree).
"""

from collections import defaultdict
from typing import Optional

from sqlmodel import Session, select

from backend.calendar.models import Period, PeriodType


class UnknownPeriod(Exception):
    pass


def load_period_hierarchy(session: Session) -> tuple[dict[str, Period], dict[str, list[str]]]:
    periods = session.exec(select(Period)).all()
    period_by_code = {p.code: p for p in periods}
    children_by_parent: dict[str, list[str]] = defaultdict(list)
    for p in periods:
        if p.parent_code:
            children_by_parent[p.parent_code].append(p.code)
    return period_by_code, children_by_parent


def month_indices_for(
    period_by_code: dict[str, Period],
    children_by_parent: dict[str, list[str]],
    period_code: Optional[str],
) -> Optional[set[int]]:
    """Which of the year's 12 monthly-array slots (0-based) a period covers.

    None means "the whole year" — either no period was requested, or the
    requested period is itself the Year — callers treat that as "sum everything".
    """
    if period_code is None:
        return None
    period = period_by_code.get(period_code)
    if period is None:
        raise UnknownPeriod(period_code)
    if period.period_type == PeriodType.YEAR:
        return None

    def collect_month_orders(code: str) -> set[int]:
        node = period_by_code[code]
        if node.period_type == PeriodType.MONTH:
            return {node.order - 1}
        result: set[int] = set()
        for child in children_by_parent.get(code, []):
            result |= collect_month_orders(child)
        return result

    return collect_month_orders(period_code)


def ytd_month_indices_for(
    period_by_code: dict[str, Period],
    children_by_parent: dict[str, list[str]],
    period_code: Optional[str],
) -> Optional[set[int]]:
    """Cumulative fiscal-year-start-through-period coverage, for YTD scoping
    (see docs/adr/0034, docs/adr/0037). `order` is fiscal-year-relative and
    sequential (1-12 for Month, 1-4 for Quarter — see docs/adr/0032), so a
    Quarter's last covered month is simply `order * 3`. A Year period already
    covers every month, so it's unaffected by YTD — None, same as non-YTD.
    """
    if period_code is None:
        return None
    period = period_by_code.get(period_code)
    if period is None:
        raise UnknownPeriod(period_code)
    if period.period_type == PeriodType.YEAR:
        return None
    if period.period_type == PeriodType.QUARTER:
        return set(range(period.order * 3))
    return set(range(period.order))


def ordered_month_codes_of_year(
    period_by_code: dict[str, Period],
    children_by_parent: dict[str, list[str]],
    year_code: str,
) -> list[str]:
    """One Year's 12 Month codes, chronological (Jan..Dec) order — shared by
    gl_tree.py's load_monthly()/build_tree() and vdt_tree.py's
    build_vdt_tree(), both of which need an explicit ordered window to
    restrict fact-loading to one fiscal year's months and avoid silently
    summing e.g. FY24-M01 and FY26-M01 into the same slot (see docs/adr/0032).
    """
    codes = [
        month_code
        for quarter_code in children_by_parent.get(year_code, [])
        for month_code in children_by_parent.get(quarter_code, [])
    ]
    codes.sort(key=lambda c: period_by_code[c].order)
    return codes


def _year_order_of(period_by_code: dict[str, Period], code: str) -> int:
    node = period_by_code[code]
    while node.period_type != PeriodType.YEAR:
        node = period_by_code[node.parent_code]
    return node.order


def trailing_month_codes(
    period_by_code: dict[str, Period],
    children_by_parent: dict[str, list[str]],
    anchor_month_code: str,
    window_length: int = 12,
) -> list[str]:
    """Up to `window_length` Month codes ending at (and including)
    `anchor_month_code`, walking backward across fiscal-year sibling roots —
    the VDT Trends Trailing mode window (see docs/adr/0042). Chronological
    (oldest first) order, same as ordered_month_codes_of_year().

    Returns fewer than `window_length` codes if history runs out before the
    window is full (e.g. an anchor near the earliest seeded fiscal year) —
    a partial window is a deliberate, expected result here, not an error
    (see the ADR's "no enforced minimum" decision), mirroring how production
    will genuinely start with less than a year of operational history.
    """
    anchor = period_by_code.get(anchor_month_code)
    if anchor is None:
        raise UnknownPeriod(anchor_month_code)
    if anchor.period_type != PeriodType.MONTH:
        raise UnknownPeriod(anchor_month_code)

    years_by_order = {
        p.order: p for p in period_by_code.values() if p.period_type == PeriodType.YEAR
    }

    months_cache: dict[int, list[str]] = {}

    def months_of(year_order: int) -> list[str]:
        if year_order not in months_cache:
            year = years_by_order.get(year_order)
            months_cache[year_order] = (
                ordered_month_codes_of_year(period_by_code, children_by_parent, year.code) if year else []
            )
        return months_cache[year_order]

    result: list[str] = []
    year_order = _year_order_of(period_by_code, anchor_month_code)
    month_order = anchor.order
    while len(result) < window_length and year_order >= 1:
        months = months_of(year_order)
        if not months:
            break
        result.append(months[month_order - 1])
        month_order -= 1
        if month_order < 1:
            year_order -= 1
            month_order = 12

    result.reverse()
    return result


def calendar_month_label(period: Period) -> str:
    """A Month period's label reformatted calendar-style, e.g. "Sep FY25" ->
    "Sep '25" — used by Trailing mode's column headers, where the plain
    "Sep FY25" fiscal-year-qualified label would be needlessly verbose next
    to Financial Year mode's bare month names, and a bare month name alone
    would be ambiguous once a window can repeat a month name across two
    fiscal years (see docs/adr/0042). Fiscal years are calendar-aligned
    (Jan start — see seed.py's FISCAL_YEARS comment), so this is a pure
    reformat, not a real calendar conversion.
    """
    month_name, fiscal_year = period.label.rsplit(" ", 1)
    return f"{month_name} '{fiscal_year[-2:]}"


def build_period_tree(session: Session) -> dict[str, dict]:
    period_by_code, children_by_parent = load_period_hierarchy(session)
    return {
        code: {
            "id": code,
            "label": period.label,
            "periodType": period.period_type.value,
            "parentId": period.parent_code,
            "childIds": sorted(children_by_parent.get(code, []), key=lambda c: period_by_code[c].order),
            "order": period.order,
        }
        for code, period in period_by_code.items()
    }
