"""Contract tests for absolute monetary storage, rounding, and company currency."""

from decimal import Decimal

from sqlmodel import select

from backend.drivers.engine import DriverEngine
from backend.models import DriverFact, HierarchyKind, Source
from backend.scripts.seed import build_company_hierarchy, build_company_nodes

from conftest import fixture_graph  # noqa: E402


def test_company_master_is_loaded_from_csv_with_iso_currency():
    hierarchy = build_company_hierarchy()
    bu_node_codes = {n.code for n in hierarchy if n.hierarchy_kind == HierarchyKind.BU}
    companies = build_company_nodes(bu_node_codes)
    company_0190 = next(node for node in companies if node.code == "0190")
    company_0007 = next(node for node in companies if node.code == "0007")

    assert company_0190.label == "MISC Ship Management SB"
    assert company_0190.currency == "MYR"
    assert company_0190.bu_node_code == "MISCM"
    assert company_0007.currency == "USD"
    assert len({node.code for node in companies}) == len(companies)

    root = next(n for n in hierarchy if n.parent_code is None)
    assert root.code == "MISC_GROUP"
    assert next(n for n in hierarchy if n.code == "MISC").parent_code == "MISC_GROUP"


def test_formula_money_target_rounds_half_up_per_company_month(session):
    codes = fixture_graph(session)
    january_rate = session.exec(
        select(DriverFact).where(
            DriverFact.code == codes["driver_base_rate"],
            DriverFact.year == codes["year"],
            DriverFact.period == 1,
            DriverFact.source == Source.ACTUAL,
        )
    ).one()
    january_rate.amount = Decimal("0.000500")
    session.add(january_rate)
    session.commit()

    periods = [(codes["year"], i) for i in range(1, 13)]
    engine = DriverEngine(session, [codes["company"]], periods)
    monthly = engine.target_value(codes["va_driven"], "actual")

    # Headcount 10 × rate 0.0005 = 0.005, rounded at the final monetary
    # Company × Month × Source target boundary using ROUND_HALF_UP.
    assert monthly[0] == Decimal("0.01")
