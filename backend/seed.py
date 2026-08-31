"""Rebuild backend/data/zeteo.db from the real GL/FSI hierarchy plus fake facts.

Source of truth for the hierarchy is docs/anaplan_is_master_data.csv (a real
SAP GL/FSI export). Fact amounts are fabricated with a fixed RNG seed so the
dataset is reproducible. See docs/adr/0022, 0023, 0024.

Run with: python backend/seed.py
"""

import csv
import json
import random
from pathlib import Path

from sqlmodel import Session, delete

from db import engine, init_db
from models import (
    CompanyNode,
    CompanyNodeType,
    Driver,
    DriverFact,
    DriverFormula,
    DriverFormulaTerm,
    FormulaOperator,
    GLFact,
    GLNode,
    NodeType,
    NormalBalance,
    OperationalUnit,
    Period,
    PeriodType,
    Scenario,
)

REPO_ROOT = Path(__file__).parent.parent
CSV_PATH = REPO_ROOT / "docs" / "anaplan_is_master_data.csv"
COMPANIES_JSON_PATH = Path(__file__).parent / "data" / "companies.json"

SEED = 42
MONTHS = range(1, 13)

# Root of the Business chip's hierarchy — see docs/adr/0028. Not itself in
# companies.json (that file only holds the real BU/Company data); synthesised
# here the same way build_periods() synthesises FY26's Year row.
GROUP_CODE = "MISC"
GROUP_LABEL = "MISC Group"

# One fiscal year, calendar-aligned (Jan start) — see docs/adr/0025. The
# schema doesn't prevent more years, this just isn't asked to carry them yet.
FISCAL_YEAR = "FY26"
QUARTER_MONTHS = {1: (1, 2, 3), 2: (4, 5, 6), 3: (7, 8, 9), 4: (10, 11, 12)}
MONTH_LABELS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def month_period_code(month: int) -> str:
    return f"{FISCAL_YEAR}-M{month:02d}"


def build_periods() -> list[Period]:
    periods = [Period(code=FISCAL_YEAR, label=FISCAL_YEAR, parent_code=None, period_type=PeriodType.YEAR, order=1)]
    for quarter, months in QUARTER_MONTHS.items():
        quarter_code = f"{FISCAL_YEAR}-Q{quarter}"
        periods.append(Period(code=quarter_code, label=f"Q{quarter}", parent_code=FISCAL_YEAR, period_type=PeriodType.QUARTER, order=quarter))
        for month in months:
            periods.append(
                Period(
                    code=month_period_code(month),
                    label=MONTH_LABELS[month - 1],
                    parent_code=quarter_code,
                    period_type=PeriodType.MONTH,
                    order=month,
                )
            )
    return periods


# 3 companies per BU, or all of them where a BU has 3 or fewer, carry fake
# fact data — see docs/adr/0024.
SAMPLED_PER_BU = 3


def build_company_nodes() -> list[CompanyNode]:
    data = json.loads(COMPANIES_JSON_PATH.read_text(encoding="utf-8"))
    nodes = [CompanyNode(code=GROUP_CODE, label=GROUP_LABEL, parent_code=None, node_type=CompanyNodeType.GROUP, order=1)]
    for bu_order, bu in enumerate(data["businessUnits"], start=1):
        nodes.append(
            CompanyNode(code=bu["code"], label=bu["label"], parent_code=GROUP_CODE, node_type=CompanyNodeType.BUSINESS_UNIT, order=bu_order)
        )
        for company_order, company in enumerate(bu["companies"], start=1):
            nodes.append(
                CompanyNode(
                    code=company["code"],
                    label=company["name"],
                    parent_code=bu["code"],
                    node_type=CompanyNodeType.COMPANY,
                    order=company_order,
                    is_sampled=company_order <= SAMPLED_PER_BU,
                )
            )
    return nodes


def sampled_company_codes(company_nodes: list[CompanyNode]) -> list[str]:
    return [n.code for n in company_nodes if n.node_type == CompanyNodeType.COMPANY and n.is_sampled]


# First digit of a Posting GL Account code -> normal balance, derived from the
# CSV itself (docs/adr/0023): every leaf under a given SAP account-number
# range is uniformly one category (Revenue=4, Cost of Revenue=5,
# Other Operating Income=6, Opex/Finance/Tax=7, Cost Allocation=8).
NORMAL_BALANCE_BY_PREFIX = {
    "4": NormalBalance.CREDIT,
    "5": NormalBalance.DEBIT,
    "6": NormalBalance.CREDIT,
    "7": NormalBalance.DEBIT,
    "8": NormalBalance.DEBIT,
}

NODE_TYPE_BY_CSV_VALUE = {
    "Reporting Root": NodeType.REPORTING_ROOT,
    "Reporting Node": NodeType.REPORTING_NODE,
    "Posting GL Account": NodeType.POSTING_GL_ACCOUNT,
}

# Legacy context-only Drivers (formerly Operational Driver GLNode rows, old
# mock's 6 curated revenue segments remapped onto the real CSV's revenue
# Posting GL Account leaves — not a 1:1 name match, best-effort per
# docs/adr/0023). Migrated into the Driver table per docs/adr/0030: no
# Formula computes them, so `displayed_under` is what keeps them rendering
# below the leaf they've always explained (see docs/adr/0029).
# (code, description, unit, value_range, displayed_under)
LEGACY_DRIVERS = [
    ("OPD-0001", "Avg. Daily Charter Rate", OperationalUnit.USD_PER_DAY, (18000, 32000), "4010100100"),
    ("OPD-0002", "Utilization / On-hire Rate", OperationalUnit.PERCENT, (92, 99), "4010100100"),
    ("OPD-0003", "Off-hire Days (fleet)", OperationalUnit.DAYS, (2, 12), "4010100100"),
    ("OPD-0004", "Avg. Spot/Voyage TCE Rate", OperationalUnit.USD_PER_DAY, (15000, 45000), "4030100500"),
    ("OPD-0005", "Spot Voyage Days (fleet)", OperationalUnit.DAYS, (10, 28), "4030100500"),
    ("OPD-0006", "Avg. Daily Charter Rate (Finance Lease)", OperationalUnit.USD_PER_DAY, (20000, 38000), "4020100100"),
    ("OPD-0007", "Fleet Uptime / Availability", OperationalUnit.PERCENT, (94, 99.5), "4020100100"),
    ("OPD-0008", "Avg. Project Completion Rate", OperationalUnit.PERCENT, (40, 95), "4050100200"),
    ("OPD-0009", "Active Projects", OperationalUnit.COUNT, (2, 9), "4050100200"),
    ("OPD-0010", "Demurrage Days Billed", OperationalUnit.DAYS, (5, 20), "4040100300"),
    ("OPD-0011", "Vessels Under Management", OperationalUnit.COUNT, (8, 25), "4060100100"),
    ("OPD-0012", "Avg. Fee per Vessel", OperationalUnit.USD_PER_MONTH, (12000, 28000), "4060100100"),
]

# Fictitious POC drivers demonstrating Driver Formula composition, reuse and
# recursion — see docs/adr/0030. Bound to real Manpower Cost leaves under
# PNL-0088 "Crew Costs (Payroll & Statutory)" (docs/anaplan_is_master_data.csv).
# `value_range=None` marks a Formula-driven driver: no facts are generated for
# it, its value is always computed (see DRIVER_FORMULAS below).
#
# No unit conversion happens between a Driver's own value and the RM_M scale
# its Formula's target leaf expects (see docs/adr/0030) — currency-flavoured
# drivers here are deliberately expressed already-in-RM_M (e.g. 0.001 means
# "RM 1,000/head/month"), the formula author's job, so Complement x RankMix x
# PayrollRate lands in the same RM_M ballpark as every other GL leaf.
MANPOWER_DRIVERS = [
    ("DRV-0001", "Crew Complement", OperationalUnit.COUNT, (700, 950), None),
    ("DRV-0002", "Rank Mix Factor", OperationalUnit.RATIO, (1.15, 1.40), None),
    ("DRV-0003", "Base Payroll Rate", OperationalUnit.USD_PER_MONTH, (0.0009, 0.0011), None),
    ("DRV-0004", "Annual Increment Factor", OperationalUnit.RATIO, (1.02, 1.08), None),
    ("DRV-0005", "Payroll Rate", OperationalUnit.USD_PER_MONTH, None, None),
    ("DRV-0006", "Contribution Base", OperationalUnit.USD_PER_MONTH, (0.05, 0.09), None),
    ("DRV-0007", "EPF Rate", OperationalUnit.RATIO, (0.12, 0.14), None),
]

DRIVERS = LEGACY_DRIVERS + MANPOWER_DRIVERS

# (code, description, target_code, sign, terms)
# terms: list of (term_index, operand_index, driver_code, operator)
DRIVER_FORMULAS = [
    (
        "FORM-0001",
        "Crew Salary & Wages Formula",
        "5100100100",  # COS-Crew costs-Salary & Wages
        1,
        [
            (0, 0, "DRV-0001", FormulaOperator.MULTIPLY),
            (0, 1, "DRV-0002", FormulaOperator.MULTIPLY),
            (0, 2, "DRV-0005", FormulaOperator.MULTIPLY),
            (1, 0, "DRV-0006", FormulaOperator.MULTIPLY),
        ],
    ),
    (
        "FORM-0002",
        "Payroll Rate Formula",
        "DRV-0005",  # Payroll Rate — recursion: a Driver driven by a Formula
        1,
        [
            (0, 0, "DRV-0003", FormulaOperator.MULTIPLY),
            (0, 1, "DRV-0004", FormulaOperator.MULTIPLY),
        ],
    ),
    (
        "FORM-0003",
        "Crew EPF Formula",
        "5100100800",  # COS-Crew costs-EPF
        1,
        [
            (0, 0, "DRV-0001", FormulaOperator.MULTIPLY),
            (0, 1, "DRV-0002", FormulaOperator.MULTIPLY),
            (0, 2, "DRV-0005", FormulaOperator.MULTIPLY),
            (0, 3, "DRV-0007", FormulaOperator.MULTIPLY),
        ],
    ),
]

# The one node that keeps full Driver Diagnostic depth (trend/drivers/
# benchmark/root-cause) — see docs/adr/0022.
FULLY_MODELLED_NODE = "PNL-0024"

# Target ANNUAL total per company (RM_M) for each account-code-prefix
# category, tuned so the fabricated P&L nets to a plausible ~15% margin
# (Revenue 800, COGS 520 -> 35% gross margin, minus opex/other -> NPAT ~125).
# Divided by each category's real leaf count (from the CSV) to get a per-leaf
# mean; individual leaves/companies then vary around that mean.
CATEGORY_ANNUAL_TARGET = {
    "4": 800.0,  # Revenue
    "5": 520.0,  # Cost of Revenue
    "6": 40.0,  # Other Operating Income
    "7": 180.0,  # Other Operating Expenses / Finance Costs / Clearing / Tax
    "8": 15.0,  # Secondary Cost Elements (internal allocations)
}


def load_hierarchy_nodes() -> list[GLNode]:
    rows = list(csv.DictReader(CSV_PATH.open(encoding="utf-8-sig")))
    by_code = {r["Code"]: r for r in rows}
    children: dict[str, list[str]] = {}
    for r in rows:
        if r["Parent Code"]:
            children.setdefault(r["Parent Code"], []).append(r["Code"])

    def leaf_normal_balances(code: str) -> set[NormalBalance]:
        r = by_code[code]
        if r["Node Type"] == "Posting GL Account":
            return {NORMAL_BALANCE_BY_PREFIX[code[0]]}
        result: set[NormalBalance] = set()
        for child in children.get(code, []):
            result |= leaf_normal_balances(child)
        return result

    nodes = []
    for r in rows:
        node_type = NODE_TYPE_BY_CSV_VALUE[r["Node Type"]]
        if node_type == NodeType.POSTING_GL_ACCOUNT:
            normal_balance = NORMAL_BALANCE_BY_PREFIX[r["Code"][0]]
        else:
            balances = leaf_normal_balances(r["Code"])
            normal_balance = balances.pop() if len(balances) == 1 else None
        nodes.append(
            GLNode(
                code=r["Code"],
                description=r["Description"],
                parent_code=r["Parent Code"] or None,
                node_type=node_type,
                level=int(r["Hierarchy Level"]),
                normal_balance=normal_balance,
            )
        )
    return nodes


def load_drivers() -> list[Driver]:
    return [
        Driver(code=code, description=description, unit=unit, displayed_under=displayed_under)
        for code, description, unit, _value_range, displayed_under in DRIVERS
    ]


def load_driver_formulas() -> tuple[list[DriverFormula], list[DriverFormulaTerm]]:
    formulas = []
    terms = []
    for code, description, target_code, sign, term_defs in DRIVER_FORMULAS:
        formulas.append(DriverFormula(code=code, description=description, target_code=target_code, sign=sign))
        for term_index, operand_index, driver_code, operator in term_defs:
            terms.append(
                DriverFormulaTerm(
                    formula_code=code,
                    term_index=term_index,
                    operand_index=operand_index,
                    driver_code=driver_code,
                    operator=operator,
                )
            )
    return formulas, terms


def monthly_curve(rng: random.Random, annual_total: float) -> list[float]:
    """A noisy seasonal monthly split of an annual total, summing back to it."""
    seasonality = [0.9, 0.85, 0.95, 1.0, 1.05, 1.1, 1.1, 1.05, 1.0, 0.95, 1.0, 1.05]
    weights = [s * rng.uniform(0.85, 1.15) for s in seasonality]
    total_weight = sum(weights)
    return [round(annual_total * w / total_weight, 3) for w in weights]


def prorate(monthly_actual: list[float], scaled_total: float) -> list[float]:
    actual_total = sum(monthly_actual)
    if actual_total == 0:
        return [0.0] * 12
    return [round(v * scaled_total / actual_total, 3) for v in monthly_actual]


def generate_gl_facts(rng: random.Random, leaves: list[GLNode], companies: list[str]) -> list[GLFact]:
    leaf_count_by_prefix = {prefix: sum(1 for leaf in leaves if leaf.code[0] == prefix) for prefix in CATEGORY_ANNUAL_TARGET}
    leaf_mean_by_prefix = {prefix: CATEGORY_ANNUAL_TARGET[prefix] / count for prefix, count in leaf_count_by_prefix.items()}

    facts = []
    for leaf in leaves:
        leaf_mean = leaf_mean_by_prefix[leaf.code[0]]
        for company in companies:
            annual_actual = rng.uniform(0.3, 1.7) * leaf_mean
            monthly_actual = monthly_curve(rng, annual_actual)
            monthly_budget = prorate(monthly_actual, annual_actual * rng.uniform(0.9, 1.1))
            monthly_prior = prorate(monthly_actual, annual_actual * rng.uniform(0.85, 1.15))
            for month in MONTHS:
                i = month - 1
                period_code = month_period_code(month)
                facts.append(GLFact(code=leaf.code, company=company, period_code=period_code, scenario=Scenario.ACTUAL, amount=monthly_actual[i]))
                facts.append(GLFact(code=leaf.code, company=company, period_code=period_code, scenario=Scenario.BUDGET, amount=monthly_budget[i]))
                facts.append(GLFact(code=leaf.code, company=company, period_code=period_code, scenario=Scenario.PRIOR_YEAR, amount=monthly_prior[i]))
    return facts


def generate_driver_facts(rng: random.Random, companies: list[str]) -> list[DriverFact]:
    """Fabricated actual/budget/prior-year values for every terminal Driver.

    Formula-driven Drivers (`value_range is None`, e.g. Payroll Rate) get no
    facts at all — their value is always computed via DriverEngine, never
    stored (see docs/adr/0030).
    """
    facts = []
    for code, _description, _unit, value_range, _displayed_under in DRIVERS:
        if value_range is None:
            continue
        lo, hi = value_range
        for company in companies:
            base_actual = rng.uniform(lo, hi)
            base_budget = min(max(base_actual * rng.uniform(0.95, 1.05), lo), hi)
            base_prior = min(max(base_actual * rng.uniform(0.90, 1.10), lo), hi)
            for scenario, base in ((Scenario.ACTUAL, base_actual), (Scenario.BUDGET, base_budget), (Scenario.PRIOR_YEAR, base_prior)):
                for month in MONTHS:
                    drift = rng.uniform(-0.05, 0.05) * (hi - lo)
                    value = min(max(base + drift * month / 12, lo), hi)
                    facts.append(
                        DriverFact(code=code, company=company, period_code=month_period_code(month), scenario=scenario, amount=round(value, 6))
                    )
    return facts


def main() -> None:
    rng = random.Random(SEED)

    hierarchy = load_hierarchy_nodes()
    drivers = load_drivers()
    driver_formulas, driver_formula_terms = load_driver_formulas()
    periods = build_periods()
    company_nodes = build_company_nodes()

    leaves = [n for n in hierarchy if n.node_type == NodeType.POSTING_GL_ACCOUNT]
    companies = sampled_company_codes(company_nodes)

    facts = generate_gl_facts(rng, leaves, companies)
    driver_facts = generate_driver_facts(rng, companies)

    init_db()
    with Session(engine) as session:
        session.exec(delete(GLFact))
        session.exec(delete(DriverFact))
        session.exec(delete(DriverFormulaTerm))
        session.exec(delete(DriverFormula))
        session.exec(delete(Driver))
        session.exec(delete(GLNode))
        session.exec(delete(Period))
        session.exec(delete(CompanyNode))
        session.commit()

        session.add_all(hierarchy)
        session.add_all(drivers)
        session.add_all(periods)
        session.add_all(company_nodes)
        session.commit()

        session.add_all(driver_formulas)
        session.commit()
        session.add_all(driver_formula_terms)
        session.commit()

        session.add_all(facts)
        session.add_all(driver_facts)
        session.commit()

    print(f"Seeded {len(hierarchy)} GL/FSI nodes")
    print(f"Seeded {len(drivers)} drivers, {len(driver_formulas)} driver formulas ({len(driver_formula_terms)} terms)")
    print(f"Seeded {len(periods)} periods ({FISCAL_YEAR}: 1 year + 4 quarters + 12 months)")
    print(f"Seeded {len(company_nodes)} company nodes ({GROUP_LABEL} + BUs + companies, {len(companies)} sampled)")
    print(f"Seeded {len(facts)} GL facts + {len(driver_facts)} driver facts across {len(companies)} sampled companies")
    print(f"Fully-modelled example node: {FULLY_MODELLED_NODE}")


if __name__ == "__main__":
    main()
