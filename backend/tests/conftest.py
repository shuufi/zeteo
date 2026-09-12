"""Shared pytest fixtures — first test infrastructure in this repo.

Uses an in-memory SQLite engine (StaticPool so the same in-memory DB survives
across the session's connections) rather than backend/data/runtime/zeteo.db, so tests
are hermetic and don't depend on running `python backend/seed.py` first.

`fixture_graph()` builds a small, hand-authored graph exercising the specific
things Phase 1 of docs/adr/0033's implementation needs covered:
  - a plain GL passthrough leaf, untouched by any VDT override
  - a GL Reporting Node (COR) whose children get wholesale-replaced by
    VDT Hierarchy Nodes in the VDT tree — its old GL children become
    unreachable there (see vdt_tree.py's module docstring)
  - a VDT Hierarchy Node nested two levels deep
  - two VDT Accounts anchored to the same FA GL code (many-to-one)
  - one of them Driver-Formula-driven with one level of Driver-Formula
    recursion (D2 is itself computed by a second Formula from D3), the other
    left undriven on purpose to exercise the "no formula bound" fallback
"""

import pytest
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.pool import StaticPool

from backend.models import (
    Company,
    CompanyHierarchy,
    Driver,
    DriverFact,
    DriverFormula,
    DriverFormulaTerm,
    Financial,
    FormulaOperator,
    GLAccount,
    GLHierarchy,
    HierarchyKind,
    NormalBalance,
    OperationalUnit,
    Period,
    PeriodType,
    Source,
    VdtAccount,
    VdtHierarchy,
)

YEAR = "FY24"
COMPANY = "C1"
MONTH_LABELS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


@pytest.fixture
def session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def _build_periods() -> list[Period]:
    periods = [Period(code=YEAR, label=YEAR, parent_code=None, period_type=PeriodType.YEAR, order=1)]
    month = 1
    for quarter in range(1, 5):
        quarter_code = f"{YEAR}-Q{quarter}"
        periods.append(Period(code=quarter_code, label=f"Q{quarter} {YEAR}", parent_code=YEAR, period_type=PeriodType.QUARTER, order=quarter))
        for _ in range(3):
            month_code = f"{YEAR}-M{month:02d}"
            periods.append(
                Period(code=month_code, label=f"{MONTH_LABELS[month - 1]} {YEAR}", parent_code=quarter_code, period_type=PeriodType.MONTH, order=month)
            )
            month += 1
    return periods


def fixture_graph(session: Session) -> dict[str, str]:
    """Seeds the graph described in this module's docstring. Returns a dict of
    the codes tests need to reference, keyed by role."""
    codes = {
        "root": "NPAT",
        "rev": "REV",
        "gl_leaf_rev": "GLLEAF-REV",
        "cor": "COR",
        "gl_old_node": "COR-OLD",
        "gl_old_leaf": "GLLEAF-OLD",
        "gl_anchor_leaf": "GLLEAF-ANCHOR",
        "act_top": "ACT-TOP",
        "act_sub": "ACT-SUB",
        "va_driven": "VA-1",
        "va_undriven": "VA-2",
        "driver_headcount": "DRV-HEADCOUNT",
        "driver_rate": "DRV-RATE",
        "driver_base_rate": "DRV-BASERATE",
        "formula_va1": "FORMULA-VA1",
        "formula_rate": "FORMULA-RATE",
        "year": YEAR,
        "company": COMPANY,
        "business_unit": "BU1",
        "group": "GROUP1",
    }

    gl_hierarchy_nodes = [
        GLHierarchy(code=codes["root"], description="Net Profit After Tax", parent_code=None),
        GLHierarchy(code=codes["rev"], description="Revenue", parent_code=codes["root"]),
        GLHierarchy(code=codes["cor"], description="Cost of Revenue", parent_code=codes["root"]),
        GLHierarchy(code=codes["gl_old_node"], description="Old Reporting Node", parent_code=codes["cor"]),
    ]

    gl_accounts = [
        GLAccount(
            code=codes["gl_leaf_rev"],
            description="Revenue Leaf",
            parent_code=codes["rev"],
            normal_balance=NormalBalance.CREDIT,
        ),
        GLAccount(
            code=codes["gl_old_leaf"],
            description="Old GL Leaf",
            parent_code=codes["gl_old_node"],
            normal_balance=NormalBalance.DEBIT,
        ),
        GLAccount(
            code=codes["gl_anchor_leaf"],
            description="Anchor GL Leaf",
            parent_code=codes["cor"],
            normal_balance=NormalBalance.DEBIT,
        ),
    ]

    vdt_hierarchy_nodes = [
        VdtHierarchy(code=codes["act_top"], description="Top Activity", parent_code=codes["cor"], level=2),
        VdtHierarchy(code=codes["act_sub"], description="Sub Activity", parent_code=codes["act_top"], level=3),
    ]

    accounts = [
        VdtAccount(
            code=codes["va_driven"], description="Driven Account", parent_code=codes["act_sub"], fa_gl_code=codes["gl_anchor_leaf"]
        ),
        VdtAccount(
            code=codes["va_undriven"], description="Undriven Account", parent_code=codes["act_sub"], fa_gl_code=codes["gl_anchor_leaf"]
        ),
    ]

    drivers = [
        Driver(code=codes["driver_headcount"], description="Headcount", unit=OperationalUnit.COUNT),
        Driver(code=codes["driver_base_rate"], description="Base Rate", unit=OperationalUnit.CURRENCY_PER_MONTH),
        Driver(code=codes["driver_rate"], description="Rate", unit=OperationalUnit.CURRENCY_PER_MONTH),
    ]

    formulas = [
        DriverFormula(code=codes["formula_rate"], description="Rate Formula", target_code=codes["driver_rate"], sign=1),
        DriverFormula(code=codes["formula_va1"], description="VA-1 Formula", target_code=codes["va_driven"], sign=1),
    ]
    formula_terms = [
        DriverFormulaTerm(
            formula_code=codes["formula_rate"], term_index=0, operand_index=0, driver_code=codes["driver_base_rate"], operator=FormulaOperator.MULTIPLY
        ),
        DriverFormulaTerm(
            formula_code=codes["formula_va1"], term_index=0, operand_index=0, driver_code=codes["driver_headcount"], operator=FormulaOperator.MULTIPLY
        ),
        DriverFormulaTerm(
            formula_code=codes["formula_va1"], term_index=0, operand_index=1, driver_code=codes["driver_rate"], operator=FormulaOperator.MULTIPLY
        ),
    ]

    periods = _build_periods()
    company_hierarchy_nodes = [
        CompanyHierarchy(code=codes["group"], label="Group One", parent_code=None, hierarchy_kind=HierarchyKind.BU, order=1),
        CompanyHierarchy(
            code=codes["business_unit"],
            label="Business Unit One",
            parent_code=codes["group"],
            hierarchy_kind=HierarchyKind.BU,
            order=1,
        ),
    ]
    company_nodes = [
        Company(
            code=COMPANY,
            label="Company One",
            bu_node_code=codes["business_unit"],
            order=1,
            is_sampled=True,
            currency="MYR",
        ),
    ]

    gl_facts = []
    driver_facts = []
    for month in range(1, 13):
        period_code = f"{YEAR}-M{month:02d}"
        gl_facts.append(Financial(code=codes["gl_leaf_rev"], company=COMPANY, period_code=period_code, source=Source.ACTUAL, amount=100.0))
        gl_facts.append(Financial(code=codes["gl_leaf_rev"], company=COMPANY, period_code=period_code, source=Source.BUDGET, amount=90.0))
        gl_facts.append(Financial(code=codes["gl_old_leaf"], company=COMPANY, period_code=period_code, source=Source.ACTUAL, amount=50.0))
        gl_facts.append(Financial(code=codes["gl_old_leaf"], company=COMPANY, period_code=period_code, source=Source.BUDGET, amount=45.0))
        gl_facts.append(Financial(code=codes["gl_anchor_leaf"], company=COMPANY, period_code=period_code, source=Source.ACTUAL, amount=30.0))
        gl_facts.append(Financial(code=codes["gl_anchor_leaf"], company=COMPANY, period_code=period_code, source=Source.BUDGET, amount=28.0))

        driver_facts.append(DriverFact(code=codes["driver_headcount"], company=COMPANY, period_code=period_code, source=Source.ACTUAL, amount=10.0))
        driver_facts.append(DriverFact(code=codes["driver_headcount"], company=COMPANY, period_code=period_code, source=Source.BUDGET, amount=10.0))
        driver_facts.append(DriverFact(code=codes["driver_base_rate"], company=COMPANY, period_code=period_code, source=Source.ACTUAL, amount=2.0))
        driver_facts.append(DriverFact(code=codes["driver_base_rate"], company=COMPANY, period_code=period_code, source=Source.BUDGET, amount=2.0))

    session.add_all(gl_hierarchy_nodes)
    session.add_all(gl_accounts)
    session.add_all(vdt_hierarchy_nodes)
    session.add_all(accounts)
    session.add_all(drivers)
    session.add_all(formulas)
    session.add_all(formula_terms)
    session.add_all(periods)
    session.add_all(company_hierarchy_nodes)
    session.add_all(company_nodes)
    session.commit()
    session.add_all(gl_facts)
    session.add_all(driver_facts)
    session.commit()

    return codes
