"""Rebuild backend/data/zeteo.db from the real GL/FSI hierarchy plus fabricated
facts for one focus company, across three real fiscal years.

Source of truth for the hierarchy is docs/anaplan_is_master_data.csv (a real
SAP GL/FSI export). Fact amounts are fabricated with a fixed RNG seed so the
dataset is reproducible — designed (stable per-leaf cost/revenue structure,
category-level YoY growth, seasonality) rather than independently random per
row, so the P&L reads as one coherent business rather than noise. See
docs/adr/0022, 0023, 0024, 0032.

Run with: python backend/seed.py
"""

import csv
import random
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from sqlmodel import Session, SQLModel

from db import engine, init_db
from models import (
    ActivityNode,
    CompanyNode,
    CompanyNodeType,
    Driver,
    DriverFact,
    DriverFormula,
    DriverFormulaTerm,
    GLFact,
    GLNode,
    NodeType,
    NormalBalance,
    Period,
    PeriodType,
    PostingActivityAccount,
    Scenario,
)
from seed_vdt import build_crew_mix_seed, load_activity_hierarchy

REPO_ROOT = Path(__file__).parent.parent
CSV_PATH = REPO_ROOT / "docs" / "anaplan_is_master_data.csv"
COMPANIES_CSV_PATH = REPO_ROOT / "docs" / "misc_companies.csv"

SEED = 42
MONTHS = range(1, 13)

# Root of the Business chip's hierarchy — see docs/adr/0028. Not itself in
# the source CSV (which holds the real BU/Company data); synthesised here the
# same way build_periods() synthesises each year's Year row.
GROUP_CODE = "MISC"
GROUP_LABEL = "MISC Group"

BUSINESS_UNIT_LABELS = {
    "AET": "AET",
    "ALAM": "ALAM",
    "GAS": "Gas Business Unit",
    "MHB": "Malaysia Marine and Heavy Engineering",
    "CORP": "MISC",
    "MMS": "MISC Maritime Services",
    "MISCM": "MISC Ship Management",
    "OBU": "Offshore Business Unit",
}

# The source's corporate BU is coded MISC, which would collide with the
# synthetic MISC Group root in CompanyNode's shared adjacency-list namespace.
# Preserve the existing application-facing CORP identifier used for that BU.
BUSINESS_UNIT_CODES = {"MISC": "CORP"}

# Three real fiscal years, calendar-aligned (Jan start) — see docs/adr/0032,
# which replaced the single-FY26-only model. Chronological order matters:
# it's what fixes each Year row's `order` (1=oldest), which is how gl_tree.py
# finds "the prior year" of any given year.
FISCAL_YEARS = ["FY24", "FY25", "FY26"]
QUARTER_MONTHS = {1: (1, 2, 3), 2: (4, 5, 6), 3: (7, 8, 9), 4: (10, 11, 12)}
MONTH_LABELS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def month_period_code(fiscal_year: str, month: int) -> str:
    return f"{fiscal_year}-M{month:02d}"


def build_periods() -> list[Period]:
    periods = []
    for year_order, fiscal_year in enumerate(FISCAL_YEARS, start=1):
        periods.append(Period(code=fiscal_year, label=fiscal_year, parent_code=None, period_type=PeriodType.YEAR, order=year_order))
        for quarter, months in QUARTER_MONTHS.items():
            quarter_code = f"{fiscal_year}-Q{quarter}"
            # Year-qualified — three fiscal years coexist as sibling roots now
            # (see docs/adr/0032), so a bare "Jan"/"Q1" would be ambiguous in
            # any cross-year picker (e.g. Financial Comparison's period pickers).
            periods.append(
                Period(code=quarter_code, label=f"Q{quarter} {fiscal_year}", parent_code=fiscal_year, period_type=PeriodType.QUARTER, order=quarter)
            )
            for month in months:
                periods.append(
                    Period(
                        code=month_period_code(fiscal_year, month),
                        label=f"{MONTH_LABELS[month - 1]} {fiscal_year}",
                        parent_code=quarter_code,
                        period_type=PeriodType.MONTH,
                        order=month,
                    )
                )
    return periods


# Only this one company carries fabricated fact data — every other company
# still exists in the Business picker hierarchy but renders Not-yet-modelled;
# BU/Group monetary rollups remain unavailable until FX is modelled —
# see docs/adr/0024, docs/adr/0032.
FOCUS_COMPANY_CODE = "0190"


def build_company_nodes() -> list[CompanyNode]:
    rows = list(csv.DictReader(COMPANIES_CSV_PATH.open(encoding="utf-8-sig")))
    rows_by_bu: dict[str, list[dict[str, str]]] = {}
    seen_codes: set[str] = set()
    for row in rows:
        bu_code = row["Business Unit"].strip()
        company_code = row["Company Code"].strip()
        company_name = row["Company Name"].strip()
        currency = row["Currency"].strip().upper()
        if not bu_code or not company_code or not company_name or len(currency) != 3 or not currency.isalpha():
            raise ValueError(f"Invalid Company master-data row: {row}")
        if company_code in seen_codes:
            raise ValueError(f"Duplicate Company Code in {COMPANIES_CSV_PATH}: {company_code}")
        seen_codes.add(company_code)
        rows_by_bu.setdefault(bu_code, []).append({**row, "Currency": currency})

    nodes = [CompanyNode(code=GROUP_CODE, label=GROUP_LABEL, parent_code=None, node_type=CompanyNodeType.GROUP, order=1)]
    for bu_order, (source_bu_code, companies) in enumerate(rows_by_bu.items(), start=1):
        bu_code = BUSINESS_UNIT_CODES.get(source_bu_code, source_bu_code)
        nodes.append(
            CompanyNode(
                code=bu_code,
                label=BUSINESS_UNIT_LABELS.get(bu_code, bu_code),
                parent_code=GROUP_CODE,
                node_type=CompanyNodeType.BUSINESS_UNIT,
                order=bu_order,
            )
        )
        for company_order, company in enumerate(companies, start=1):
            company_code = company["Company Code"].strip()
            nodes.append(
                CompanyNode(
                    code=company_code,
                    label=company["Company Name"].strip(),
                    parent_code=bu_code,
                    node_type=CompanyNodeType.COMPANY,
                    order=company_order,
                    is_sampled=company_code == FOCUS_COMPANY_CODE,
                    currency=company["Currency"],
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

# The one node that keeps full Driver Diagnostic depth (trend/drivers/
# benchmark/root-cause) — see docs/adr/0022.
FULLY_MODELLED_NODE = "PNL-0024"

# Target FY24 ANNUAL total (absolute MYR) for MISC Ship Management for each account-
# code-prefix category — a fee-based ship management business, so smaller and
# leaner than an asset-owning shipowner BU: modest revenue, thin opex, no
# large secondary cost allocations. Tuned for a plausible ~12% NPAT margin in
# FY24 (Revenue 240, COGS 175 -> ~27% gross margin, minus opex -> NPAT ~29).
# Divided by each category's real leaf count (from the CSV) to get a per-leaf
# mean; individual leaves then vary around that mean by a stable weight (see
# LEAF_WEIGHT_RANGE) that holds across all three years — a leaf that's a big
# share of Revenue in FY24 stays a big share in FY26, only the category
# total moves.
CATEGORY_ANNUAL_TARGET_FY24 = {
    "4": 240_000_000.0,  # Revenue
    "5": 175_000_000.0,  # Cost of Revenue
    "6": 8_000_000.0,  # Other Operating Income
    "7": 42_000_000.0,  # Other Operating Expenses / Finance Costs / Clearing / Tax
    "8": 3_000_000.0,  # Secondary Cost Elements (internal allocations)
}

# Category-level YoY growth (applied FY24->FY25 and FY25->FY26) — Revenue
# outgrowing Cost of Revenue is a deliberate "improving margin" story, not
# just a flat scale-up of every line.
CATEGORY_YOY_GROWTH = {
    "4": 0.07,  # Revenue
    "5": 0.04,  # Cost of Revenue
    "6": 0.03,
    "7": 0.03,
    "8": 0.03,
}

# How far an individual leaf's share of its category can sit from the flat
# per-leaf mean — narrower than the old multi-company mock's 0.3-1.7 range,
# since this now has to read as one real company's cost structure, not a
# stand-in for dozens of unrelated companies.
LEAF_WEIGHT_RANGE = (0.7, 1.3)


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


MONEY_QUANTUM = Decimal("0.01")


def money(value: float | Decimal) -> Decimal:
    return Decimal(str(value)).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def monthly_curve(rng: random.Random, annual_total: float) -> list[Decimal]:
    """A noisy seasonal monthly split of an annual total, summing back to it."""
    seasonality = [0.9, 0.85, 0.95, 1.0, 1.05, 1.1, 1.1, 1.05, 1.0, 0.95, 1.0, 1.05]
    weights = [s * rng.uniform(0.85, 1.15) for s in seasonality]
    total_weight = sum(weights)
    values = [money(annual_total * w / total_weight) for w in weights]
    values[-1] += money(annual_total) - sum(values, Decimal("0.00"))
    return values


def prorate(monthly_actual: list[Decimal], scaled_total: float) -> list[Decimal]:
    actual_total = sum(monthly_actual, Decimal("0.00"))
    if actual_total == 0:
        return [Decimal("0.00")] * 12
    target = money(scaled_total)
    values = [(v * target / actual_total).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP) for v in monthly_actual]
    values[-1] += target - sum(values, Decimal("0.00"))
    return values


def generate_gl_facts(rng: random.Random, leaves: list[GLNode], company: str) -> list[GLFact]:
    leaf_count_by_prefix = {prefix: sum(1 for leaf in leaves if leaf.code[0] == prefix) for prefix in CATEGORY_ANNUAL_TARGET_FY24}
    leaf_mean_by_prefix = {prefix: CATEGORY_ANNUAL_TARGET_FY24[prefix] / count for prefix, count in leaf_count_by_prefix.items()}
    # Drawn once per leaf so its share of the category stays stable across
    # all three years — only the category's own YoY growth moves the total.
    leaf_weight = {leaf.code: rng.uniform(*LEAF_WEIGHT_RANGE) for leaf in leaves}

    facts = []
    for leaf in leaves:
        prefix = leaf.code[0]
        fy24_annual = leaf_mean_by_prefix[prefix] * leaf_weight[leaf.code]
        growth = CATEGORY_YOY_GROWTH[prefix]
        for year_index, fiscal_year in enumerate(FISCAL_YEARS):
            annual_actual = fy24_annual * ((1 + growth) ** year_index)
            monthly_actual = monthly_curve(rng, annual_actual)
            monthly_budget = prorate(monthly_actual, annual_actual * rng.uniform(0.93, 1.07))
            for month in MONTHS:
                i = month - 1
                period_code = month_period_code(fiscal_year, month)
                facts.append(GLFact(code=leaf.code, company=company, period_code=period_code, scenario=Scenario.ACTUAL, amount=monthly_actual[i]))
                facts.append(GLFact(code=leaf.code, company=company, period_code=period_code, scenario=Scenario.BUDGET, amount=monthly_budget[i]))
    return facts


def main() -> None:
    rng = random.Random(SEED)

    hierarchy = load_hierarchy_nodes()
    periods = build_periods()
    company_nodes = build_company_nodes()

    leaves = [n for n in hierarchy if n.node_type == NodeType.POSTING_GL_ACCOUNT]
    facts = generate_gl_facts(rng, leaves, FOCUS_COMPANY_CODE)

    # VDT (activity-based) hierarchy pilot — see docs/adr/0033. Structure
    # comes from docs/vdt-hierarchy-crew-cost.csv; `gl_level_by_code` lets
    # its Activity Nodes compute their own `level` from the parent chain
    # without a Hierarchy Level CSV column of their own.
    gl_level_by_code = {n.code: n.level for n in hierarchy}
    activity_nodes, accounts = load_activity_hierarchy(gl_level_by_code)
    vdt_drivers, vdt_formulas, vdt_terms, vdt_facts = build_crew_mix_seed(FOCUS_COMPANY_CODE, FISCAL_YEARS)

    # Seed is a full reproducible rebuild. Drop first so schema changes (such
    # as Company.currency and exact decimal amounts) cannot leave a stale
    # checked-in SQLite shape behind.
    SQLModel.metadata.drop_all(engine)
    init_db()
    with Session(engine) as session:
        # Driver/DriverFormula data (docs/adr/0030) previously stayed dropped
        # after ADR-0032 (an orphaned Formula binding with no DriverFact data
        # would compute as zero and silently override a leaf's real fabricated
        # GLFact value) — now actually repopulated, targeting the new VDT
        # hierarchy's Posting Activity Accounts rather than GL leaves, so
        # that risk doesn't apply here.
        session.add_all(hierarchy)
        session.add_all(periods)
        session.add_all(company_nodes)
        session.add_all(activity_nodes)
        session.add_all(accounts)
        session.add_all(vdt_drivers)
        session.add_all(vdt_formulas)
        session.add_all(vdt_terms)
        session.commit()

        session.add_all(facts)
        session.add_all(vdt_facts)
        session.commit()

    print(f"Seeded {len(hierarchy)} GL/FSI nodes")
    print(f"Seeded {len(periods)} periods across {len(FISCAL_YEARS)} fiscal years ({', '.join(FISCAL_YEARS)})")
    print(f"Seeded {len(company_nodes)} company nodes ({GROUP_LABEL} + BUs + companies, 1 sampled: {FOCUS_COMPANY_CODE})")
    print(f"Seeded {len(facts)} GL facts for {FOCUS_COMPANY_CODE} across {len(FISCAL_YEARS)} years")
    print(f"Seeded {len(activity_nodes)} Activity Nodes and {len(accounts)} Posting Activity Accounts (VDT hierarchy pilot — docs/adr/0033)")
    print(f"Seeded {len(vdt_drivers)} Drivers / {len(vdt_formulas)} Driver Formulas for the first 3 of {len(accounts)} Posting Activity Accounts")
    print(f"Fully-modelled example node: {FULLY_MODELLED_NODE}")


if __name__ == "__main__":
    main()
