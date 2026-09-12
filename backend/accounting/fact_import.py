"""Validated POC imports of Budget and Actual facts into Zeteo's serving model."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Literal, TextIO

from sqlalchemy import and_, delete, or_
from sqlmodel import Session, col, select

from backend.accounting.models import Financial, GLAccount, Source
from backend.calendar.models import Period, Year
from backend.drivers.models import Driver, DriverFact
from backend.organization.models import Company


DatasetType = Literal["financial", "driver"]

EXPECTED_HEADERS: dict[DatasetType, list[str]] = {
    "financial": ["company_code", "year", "period", "gl_account_code", "amount"],
    "driver": ["company_code", "year", "period", "driver_code", "value"],
}


class FactImportError(ValueError):
    """Problems that make an uploaded POC fact CSV ineligible to apply."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("\n".join(errors))


@dataclass(frozen=True)
class FactImportRow:
    company_code: str
    code: str
    year: int
    period: int
    amount: Decimal


@dataclass(frozen=True)
class FactImportPlan:
    source: Source
    dataset_type: DatasetType
    scope_label: str
    periods: list[tuple[int, int]]
    company_scope: str | None
    rows: list[FactImportRow]
    existing_fact_count: int
    skipped_row_count: int


def validate_budget_csv(
    session: Session,
    calendar_year: int,
    dataset_type: DatasetType,
    stream: TextIO,
) -> FactImportPlan:
    """Validate Budget rows for one calendar year without changing the database."""
    fiscal_year = _validate_fiscal_year(session, calendar_year)
    rows, skipped_rows = _read_matching_rows(
        session,
        dataset_type,
        stream,
        matches=lambda row: _calendar_year(row.get("year"), None) == calendar_year,
        period_for=lambda row, line, errors: _period_for_source_values(session, row.get("year"), row.get("period"), line, errors),
    )
    if not rows:
        raise FactImportError([f"No CSV rows match selected calendar year {calendar_year}."])
    periods = [(fiscal_year, month) for month in range(1, 13)]
    return _plan(
        session,
        source=Source.BUDGET,
        dataset_type=dataset_type,
        scope_label=f"{calendar_year} {dataset_type} Budget",
        periods=periods,
        company_scope=None,
        rows=rows,
        skipped_rows=skipped_rows,
    )


def validate_actual_csv(
    session: Session,
    company_code: str,
    current_actual_year: int,
    current_actual_period: int,
    dataset_type: DatasetType,
    stream: TextIO,
) -> FactImportPlan:
    """Validate Actual rows matching one Company and Current Actual Period."""
    if session.get(Company, company_code) is None:
        raise FactImportError([f"Company {company_code!r} does not exist in Zeteo's master data."])
    if session.get(Year, current_actual_year) is None or session.get(Period, current_actual_period) is None:
        raise FactImportError(
            [f"Current Actual Period {current_actual_year}-{current_actual_period:02d} is not a valid Zeteo period."]
        )

    current_period = (current_actual_year, current_actual_period)
    rows, skipped_rows = _read_matching_rows(
        session,
        dataset_type,
        stream,
        matches=lambda row: (
            (row.get("company_code") or "").strip() == company_code
            and _period_if_valid(session, row.get("year"), row.get("period")) == current_period
        ),
        period_for=lambda _row, _line, _errors: current_period,
    )
    if not rows:
        raise FactImportError(
            [f"No rows match Company {company_code!r} and Current Actual Period {current_actual_year}-{current_actual_period:02d}."],
        )
    return _plan(
        session,
        source=Source.ACTUAL,
        dataset_type=dataset_type,
        scope_label=f"{company_code} {current_actual_year}-{current_actual_period:02d} {dataset_type} Actual",
        periods=[current_period],
        company_scope=company_code,
        rows=rows,
        skipped_rows=skipped_rows,
    )


def _year_period_filter(model, periods: list[tuple[int, int]]):
    """A `year`/`period` WHERE clause matching any of `periods` — a single
    `and_` when every pair shares one year (the common case: a whole year's
    12 months for Budget, one Month for Actual), an `or_` of pairs otherwise."""
    years = {year for year, _ in periods}
    if len(years) == 1:
        (year,) = years
        return and_(model.year == year, col(model.period).in_(p for _, p in periods))
    return or_(*(and_(model.year == year, model.period == period) for year, period in periods))


def apply_fact_import(session: Session, plan: FactImportPlan) -> None:
    """Replace precisely a validated import plan's Budget or Actual fact scope."""
    model = Financial if plan.dataset_type == "financial" else DriverFact
    statement = delete(model).where(model.source == plan.source).where(_year_period_filter(model, plan.periods))
    if plan.company_scope:
        statement = statement.where(model.company == plan.company_scope)
    session.exec(statement)
    session.add_all(
        [
            model(code=row.code, company=row.company_code, year=row.year, period=row.period, source=plan.source, amount=row.amount)
            for row in plan.rows
        ],
    )
    try:
        session.commit()
    except Exception:
        session.rollback()
        raise


def _plan(
    session: Session,
    *,
    source: Source,
    dataset_type: DatasetType,
    scope_label: str,
    periods: list[tuple[int, int]],
    company_scope: str | None,
    rows: list[FactImportRow],
    skipped_rows: int,
) -> FactImportPlan:
    model = Financial if dataset_type == "financial" else DriverFact
    statement = select(model.id).where(model.source == source).where(_year_period_filter(model, periods))
    if company_scope:
        statement = statement.where(model.company == company_scope)
    return FactImportPlan(
        source=source,
        dataset_type=dataset_type,
        scope_label=scope_label,
        periods=periods,
        company_scope=company_scope,
        rows=rows,
        existing_fact_count=len(session.exec(statement).all()),
        skipped_row_count=skipped_rows,
    )


def _read_matching_rows(
    session: Session,
    dataset_type: DatasetType,
    stream: TextIO,
    *,
    matches: callable,
    period_for: callable,
) -> tuple[list[FactImportRow], int]:
    if dataset_type not in EXPECTED_HEADERS:
        raise FactImportError([f"Unknown dataset type {dataset_type!r}; use 'financial' or 'driver'."])

    reader = csv.DictReader(stream)
    expected_headers = EXPECTED_HEADERS[dataset_type]
    if reader.fieldnames != expected_headers:
        found_headers = reader.fieldnames or []
        raise FactImportError([f"Expected CSV headers {','.join(expected_headers)}; found {','.join(found_headers) or '(none)'}."])

    errors: list[str] = []
    company_codes = set(session.exec(select(Company.code)).all())
    valid_codes = _valid_codes(session, dataset_type)
    code_header, amount_header = expected_headers[3], expected_headers[4]
    rows: list[FactImportRow] = []
    seen_keys: set[tuple[str, str, int, int]] = set()
    skipped_rows = 0

    for line_number, raw_row in enumerate(reader, start=2):
        if None in raw_row:
            errors.append(f"Line {line_number}: has more values than its header declares.")
            continue
        if not matches(raw_row):
            skipped_rows += 1
            continue

        company_code = _required(raw_row, "company_code", line_number, errors)
        code = _required(raw_row, code_header, line_number, errors)
        period_result = period_for(raw_row, line_number, errors)
        amount = _amount(raw_row.get(amount_header), amount_header, line_number, errors)
        if company_code is None or code is None or period_result is None or amount is None:
            continue
        year, period = period_result
        if company_code not in company_codes:
            errors.append(f"Line {line_number}: unknown Company code {company_code!r}.")
        if code not in valid_codes:
            entity = "GL Account" if dataset_type == "financial" else "Driver"
            errors.append(f"Line {line_number}: unknown {entity} code {code!r}.")

        key = (company_code, code, year, period)
        if key in seen_keys:
            errors.append(f"Line {line_number}: duplicate Company × code × month row for {company_code!r}, {code!r}, {year}-{period:02d}.")
        seen_keys.add(key)
        rows.append(FactImportRow(company_code=company_code, code=code, year=year, period=period, amount=amount))

    if errors:
        raise FactImportError(errors)
    return rows, skipped_rows


def _validate_fiscal_year(session: Session, calendar_year: int) -> int:
    if session.get(Year, calendar_year) is None:
        raise FactImportError([f"Calendar year {calendar_year} does not map to a Fiscal Year in Zeteo's Year master data."])
    return calendar_year


def _period_for_source_values(
    session: Session,
    raw_year: str | None,
    raw_period: str | None,
    line_number: int,
    errors: list[str],
) -> tuple[int, int] | None:
    calendar_year = _calendar_year(raw_year, line_number, errors)
    period = _period_number(raw_period, line_number, errors)
    if calendar_year is None or period is None:
        return None
    resolved = _period_if_valid(session, str(calendar_year), str(period))
    if resolved is None:
        errors.append(f"Line {line_number}: year {calendar_year} and period {period} do not map to a Zeteo fiscal Year.")
    return resolved


def _period_if_valid(session: Session, raw_year: str | None, raw_period: str | None) -> tuple[int, int] | None:
    try:
        calendar_year = int((raw_year or "").strip())
        period = int((raw_period or "").strip())
    except ValueError:
        return None
    if period not in range(1, 13):
        return None
    if session.get(Year, calendar_year) is None:
        return None
    return calendar_year, period


def _valid_codes(session: Session, dataset_type: DatasetType) -> set[str]:
    model = GLAccount if dataset_type == "financial" else Driver
    return set(session.exec(select(model.code)).all())


def _required(raw_row: dict[str | None, str | None], header: str, line_number: int, errors: list[str]) -> str | None:
    value = (raw_row.get(header) or "").strip()
    if not value:
        errors.append(f"Line {line_number}: {header} is required.")
        return None
    return value


def _calendar_year(raw_year: str | None, line_number: int | None, errors: list[str] | None = None) -> int | None:
    try:
        year = int((raw_year or "").strip())
    except ValueError:
        if line_number is not None and errors is not None:
            errors.append(f"Line {line_number}: year must be a four-digit calendar year.")
        return None
    if year not in range(1000, 10000):
        if line_number is not None and errors is not None:
            errors.append(f"Line {line_number}: year must be a four-digit calendar year.")
        return None
    return year


def _period_number(raw_period: str | None, line_number: int, errors: list[str]) -> int | None:
    try:
        period = int((raw_period or "").strip())
    except ValueError:
        errors.append(f"Line {line_number}: period must be an integer from 1 to 12.")
        return None
    if period not in range(1, 13):
        errors.append(f"Line {line_number}: period must be an integer from 1 to 12.")
        return None
    return period


def _amount(raw_amount: str | None, header: str, line_number: int, errors: list[str]) -> Decimal | None:
    try:
        amount = Decimal((raw_amount or "").strip())
    except InvalidOperation:
        errors.append(f"Line {line_number}: {header} must be a decimal number.")
        return None
    if not amount.is_finite():
        errors.append(f"Line {line_number}: {header} must be a finite decimal number.")
        return None
    return amount
