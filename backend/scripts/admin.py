"""Interactive POC administration for simulation boundaries and fact imports."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlmodel import Session, select

from backend.accounting.fact_import import FactImportError, FactImportPlan, apply_fact_import, validate_actual_csv, validate_budget_csv
from backend.accounting.models import Financial, Source
from backend.application.settings import current_actual_period, set_current_actual_period
from backend.calendar.models import Period, PeriodType
from backend.drivers.models import DriverFact
from backend.infrastructure.db import engine, init_db
from backend.organization.models import Company


def main() -> int:
    init_db()
    with Session(engine) as session:
        while True:
            print("\nZeteo Admin")
            print("1. Set Current Actual Period")
            print("2. Import Budget")
            print("3. Import Actual")
            print("4. Show status")
            print("0. Exit")
            try:
                choice = input("Choose an option: ").strip()
            except EOFError:
                print("\nExiting.")
                return 0
            if choice == "0":
                return 0
            if choice == "1":
                _set_current_actual_period(session)
            elif choice == "2":
                _import_budget(session)
            elif choice == "3":
                _import_actual(session)
            elif choice == "4":
                _show_status(session)
            else:
                print("Choose 0, 1, 2, 3, or 4.")


def _set_current_actual_period(session: Session) -> None:
    try:
        year = _calendar_year(input("Calendar year (for example 2026): "))
        period = _period_number(input("Period (1-12): "))
        period_code = _period_code(session, year, period)
        set_current_actual_period(session, period_code)
        print(f"Current Actual Period set to {period_code}.")
    except ValueError as error:
        print(f"error: {error}")


def _import_budget(session: Session) -> None:
    try:
        year = _calendar_year(input("Budget calendar year: "))
        dataset_type = _dataset_type()
        path = _file_path()
        with path.open(newline="", encoding="utf-8-sig") as stream:
            plan = validate_budget_csv(session, year, dataset_type, stream)
        _confirm_and_apply(session, plan)
    except (FactImportError, ValueError) as error:
        _print_import_error(error)


def _import_actual(session: Session) -> None:
    current_period = current_actual_period(session)
    if current_period is None:
        print("Set Current Actual Period before importing Actuals.")
        return
    try:
        company_code = input("Company code: ").strip()
        dataset_type = _dataset_type()
        path = _file_path()
        with path.open(newline="", encoding="utf-8-sig") as stream:
            plan = validate_actual_csv(session, company_code, current_period, dataset_type, stream)
        _confirm_and_apply(session, plan)
    except (FactImportError, ValueError) as error:
        _print_import_error(error)


def _confirm_and_apply(session: Session, plan: FactImportPlan) -> None:
    print(
        f"Validated {len(plan.rows)} rows for {plan.scope_label}; skipped {plan.skipped_row_count} rows outside that scope. "
        f"Applying replaces {plan.existing_fact_count} existing rows.",
    )
    if input(f"Replace {plan.scope_label} facts? [y/N] ").strip().lower() not in {"y", "yes"}:
        print("Cancelled; no database changes were made.")
        return
    apply_fact_import(session, plan)
    print(f"Replaced {plan.scope_label} facts with {len(plan.rows)} CSV rows.")


def _show_status(session: Session) -> None:
    actual_period = current_actual_period(session) or "Not set"
    company_count = len(session.exec(select(Company.code)).all())
    financial_actual_count = len(session.exec(select(Financial.id).where(Financial.source == Source.ACTUAL)).all())
    financial_budget_count = len(session.exec(select(Financial.id).where(Financial.source == Source.BUDGET)).all())
    driver_actual_count = len(session.exec(select(DriverFact.id).where(DriverFact.source == Source.ACTUAL)).all())
    driver_budget_count = len(session.exec(select(DriverFact.id).where(DriverFact.source == Source.BUDGET)).all())
    print(f"Current Actual Period: {actual_period}")
    print(f"Companies: {company_count}")
    print(f"Financial facts — Actual: {financial_actual_count}; Budget: {financial_budget_count}")
    print(f"Driver facts — Actual: {driver_actual_count}; Budget: {driver_budget_count}")


def _calendar_year(value: str) -> int:
    try:
        year = int(value)
    except ValueError as error:
        raise ValueError("Calendar year must be four digits.") from error
    if year not in range(1000, 10000):
        raise ValueError("Calendar year must be four digits.")
    return year


def _period_number(value: str) -> int:
    try:
        period = int(value)
    except ValueError as error:
        raise ValueError("Period must be an integer from 1 to 12.") from error
    if period not in range(1, 13):
        raise ValueError("Period must be an integer from 1 to 12.")
    return period


def _period_code(session: Session, year: int, period: int) -> str:
    period_code = f"FY{year % 100:02d}-M{period:02d}"
    node = session.get(Period, period_code)
    if node is None or node.period_type != PeriodType.MONTH:
        raise ValueError(f"Calendar year {year} and period {period} do not map to a Zeteo Month.")
    return period_code


def _dataset_type() -> str:
    value = input("Dataset type (financial/driver): ").strip().lower()
    if value not in {"financial", "driver"}:
        raise ValueError("Dataset type must be financial or driver.")
    return value


def _file_path() -> Path:
    path = Path(input("CSV file path: ").strip())
    if not path.is_file():
        raise ValueError(f"CSV file not found: {path}")
    return path


def _print_import_error(error: FactImportError | ValueError) -> None:
    if isinstance(error, FactImportError):
        for message in error.errors:
            print(f"error: {message}")
    else:
        print(f"error: {error}")


if __name__ == "__main__":
    raise SystemExit(main())
