"""Year/Quarter/Month period hierarchy — see docs/adr/0025 and docs/adr/0032.

Mirrors gl_tree.py's adjacency-list-walk shape, but for the much smaller
period dimension (17 rows per fiscal year: 1 Year + 4 Quarters + 12 Months —
multiple fiscal years coexist as sibling Year roots, not one shared tree).
"""

from collections import defaultdict
from typing import Optional

from sqlmodel import Session, select

from models import Period, PeriodType


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


def month_codes_of_year(
    period_by_code: dict[str, Period],
    children_by_parent: dict[str, list[str]],
    year_code: str,
) -> dict[str, int]:
    """One Year's Month period codes -> their 0-based month-array index.

    Shared by gl_tree.py's load_monthly() and driver_engine.py's DriverEngine —
    both need to restrict fact-loading to one fiscal year's 12 Month codes to
    avoid silently summing e.g. FY24-M01 and FY26-M01 into the same slot (see
    docs/adr/0032).
    """
    codes: dict[str, int] = {}
    for quarter_code in children_by_parent.get(year_code, []):
        for month_code in children_by_parent.get(quarter_code, []):
            codes[month_code] = period_by_code[month_code].order - 1
    return codes


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
