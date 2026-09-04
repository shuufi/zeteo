"""Contract tests for absolute monetary storage, rounding, and company currency."""

import sys
from decimal import Decimal
from pathlib import Path

from sqlmodel import select

sys.path.insert(0, str(Path(__file__).parent.parent))

from driver_engine import DriverEngine  # noqa: E402
from models import CompanyNodeType, DriverFact, Scenario  # noqa: E402
from seed import build_company_nodes  # noqa: E402

from conftest import fixture_graph  # noqa: E402


def test_company_master_is_loaded_from_csv_with_iso_currency():
    companies = build_company_nodes()
    company_0190 = next(node for node in companies if node.code == "0190")
    company_0007 = next(node for node in companies if node.code == "0007")

    assert company_0190.node_type == CompanyNodeType.COMPANY
    assert company_0190.label == "MISC Ship Management SB"
    assert company_0190.currency == "MYR"
    assert company_0007.currency == "USD"
    assert len({node.code for node in companies}) == len(companies)
    assert next(node for node in companies if node.code == "MISC").node_type == CompanyNodeType.GROUP
    assert next(node for node in companies if node.code == "CORP").node_type == CompanyNodeType.BUSINESS_UNIT


def test_formula_money_target_rounds_half_up_per_company_month(session):
    codes = fixture_graph(session)
    january_rate = session.exec(
        select(DriverFact).where(
            DriverFact.code == codes["driver_base_rate"],
            DriverFact.period_code == f"{codes['year']}-M01",
            DriverFact.scenario == Scenario.ACTUAL,
        )
    ).one()
    january_rate.amount = Decimal("0.000500")
    session.add(january_rate)
    session.commit()

    engine = DriverEngine(session, [codes["company"]], codes["year"])
    monthly = engine.target_value(codes["va_driven"], "actual")

    # Headcount 10 × rate 0.0005 = 0.005, rounded at the final monetary
    # Company × Month × Scenario target boundary using ROUND_HALF_UP.
    assert monthly[0] == Decimal("0.01")
