from __future__ import annotations

from decimal import Decimal
from io import StringIO

import pytest
from sqlmodel import Session, col, select

from backend.accounting.fact_import import FactImportError, apply_fact_import, validate_actual_csv, validate_budget_csv
from backend.accounting.models import Financial, Source
from backend.application.settings import current_actual_period, set_current_actual_period
from backend.drivers.models import DriverFact
from backend.tests.conftest import COMPANY, YEAR, fixture_graph


def _financial_csv(*rows: str) -> StringIO:
    return StringIO("company_code,year,period,gl_account_code,amount\n" + "\n".join(rows))


def _driver_csv(*rows: str) -> StringIO:
    return StringIO("company_code,year,period,driver_code,value\n" + "\n".join(rows))


def test_budget_import_replaces_only_selected_calendar_year_budget_scope(session: Session):
    codes = fixture_graph(session)
    plan = validate_budget_csv(
        session,
        2024,
        "financial",
        _financial_csv(
            f"{COMPANY},2024,1,{codes['gl_leaf_rev']},123.45",
            f"{COMPANY},2025,1,{codes['gl_leaf_rev']},999.00",
        ),
    )

    assert plan.existing_fact_count == 36
    assert plan.skipped_row_count == 1

    apply_fact_import(session, plan)

    budget_rows = session.exec(
        select(Financial)
        .where(Financial.source == Source.BUDGET)
        .where(col(Financial.period_code).like(f"{YEAR}-%")),
    ).all()
    actual_rows = session.exec(
        select(Financial)
        .where(Financial.source == Source.ACTUAL)
        .where(col(Financial.period_code).like(f"{YEAR}-%")),
    ).all()
    driver_budget_rows = session.exec(
        select(DriverFact)
        .where(DriverFact.source == Source.BUDGET)
        .where(col(DriverFact.period_code).like(f"{YEAR}-%")),
    ).all()

    assert [(row.company, row.code, row.period_code, row.amount) for row in budget_rows] == [
        (COMPANY, codes["gl_leaf_rev"], f"{YEAR}-M01", Decimal("123.45")),
    ]
    assert len(actual_rows) == 36
    assert len(driver_budget_rows) == 24


def test_driver_budget_import_replaces_only_driver_budget_scope(session: Session):
    codes = fixture_graph(session)
    plan = validate_budget_csv(
        session,
        2024,
        "driver",
        _driver_csv(f"{COMPANY},2024,2,{codes['driver_headcount']},25"),
    )

    assert plan.existing_fact_count == 24
    apply_fact_import(session, plan)

    driver_budget_rows = session.exec(
        select(DriverFact)
        .where(DriverFact.source == Source.BUDGET)
        .where(col(DriverFact.period_code).like(f"{YEAR}-%")),
    ).all()
    financial_budget_rows = session.exec(
        select(Financial)
        .where(Financial.source == Source.BUDGET)
        .where(col(Financial.period_code).like(f"{YEAR}-%")),
    ).all()

    assert [(row.company, row.code, row.period_code, row.amount) for row in driver_budget_rows] == [
        (COMPANY, codes["driver_headcount"], f"{YEAR}-M02", Decimal("25")),
    ]
    assert len(financial_budget_rows) == 36


def test_actual_import_filters_to_selected_company_and_current_actual_period(session: Session):
    codes = fixture_graph(session)
    current_period = f"{YEAR}-M02"
    set_current_actual_period(session, current_period)

    plan = validate_actual_csv(
        session,
        COMPANY,
        current_actual_period(session) or "",
        "financial",
        _financial_csv(
            f"{COMPANY},2024,2,{codes['gl_leaf_rev']},222.22",
            f"{COMPANY},2024,3,{codes['gl_leaf_rev']},333.33",
            f"OTHER,2024,2,{codes['gl_leaf_rev']},444.44",
        ),
    )

    assert plan.existing_fact_count == 3
    assert plan.skipped_row_count == 2
    apply_fact_import(session, plan)

    actual_rows = session.exec(
        select(Financial)
        .where(Financial.source == Source.ACTUAL)
        .where(Financial.company == COMPANY)
        .where(Financial.period_code == current_period),
    ).all()
    budget_rows = session.exec(
        select(Financial)
        .where(Financial.source == Source.BUDGET)
        .where(Financial.company == COMPANY)
        .where(Financial.period_code == current_period),
    ).all()

    assert [(row.code, row.amount) for row in actual_rows] == [(codes["gl_leaf_rev"], Decimal("222.22"))]
    assert len(budget_rows) == 3


def test_invalid_matching_codes_and_duplicate_keys_reject_the_entire_csv_without_writes(session: Session):
    codes = fixture_graph(session)
    before = session.exec(select(Financial.id).where(Financial.source == Source.BUDGET)).all()

    with pytest.raises(FactImportError) as caught:
        validate_budget_csv(
            session,
            2024,
            "financial",
            _financial_csv(
                f"{COMPANY},2024,1,{codes['gl_leaf_rev']},50",
                f"{COMPANY},2024,1,{codes['gl_leaf_rev']},60",
                f"NO-SUCH-COMPANY,2024,2,{codes['gl_leaf_rev']},70",
                f"{COMPANY},2024,3,NO-SUCH-GL,80",
            ),
        )

    assert "unknown Company code 'NO-SUCH-COMPANY'" in str(caught.value)
    assert "duplicate Company × code × month row" in str(caught.value)
    assert "unknown GL Account code 'NO-SUCH-GL'" in str(caught.value)
    after = session.exec(select(Financial.id).where(Financial.source == Source.BUDGET)).all()
    assert after == before


def test_rejects_wrong_headers_unknown_calendar_year_and_no_actual_rows_in_scope(session: Session):
    codes = fixture_graph(session)

    with pytest.raises(FactImportError, match="Expected CSV headers"):
        validate_budget_csv(session, 2024, "financial", StringIO("company,amount\nC1,10\n"))

    with pytest.raises(FactImportError, match="Calendar year 2099 does not map"):
        validate_budget_csv(session, 2099, "financial", _financial_csv("C1,2099,1,GLLEAF-REV,10"))

    with pytest.raises(FactImportError, match="No rows match Company"):
        validate_actual_csv(
            session,
            COMPANY,
            f"{YEAR}-M01",
            "financial",
            _financial_csv(f"{COMPANY},2024,2,{codes['gl_leaf_rev']},10"),
        )
