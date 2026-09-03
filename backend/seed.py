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
    GLFact,
    GLNode,
    NodeType,
    NormalBalance,
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
# here the same way build_periods() synthesises each year's Year row.
GROUP_CODE = "MISC"
GROUP_LABEL = "MISC Group"

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
# still exists in the hierarchy (Business picker, BU rollups) but renders
# Not-yet-modelled, the same mechanism already used for unsampled companies —
# see docs/adr/0024, docs/adr/0032.
FOCUS_COMPANY_CODE = "0190"


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
                    is_sampled=company["code"] == FOCUS_COMPANY_CODE,
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

# Target FY24 ANNUAL total (RM_M) for MISC Ship Management for each account-
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
    "4": 240.0,  # Revenue
    "5": 175.0,  # Cost of Revenue
    "6": 8.0,  # Other Operating Income
    "7": 42.0,  # Other Operating Expenses / Finance Costs / Clearing / Tax
    "8": 3.0,  # Secondary Cost Elements (internal allocations)
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

    init_db()
    with Session(engine) as session:
        # Driver Formula demo (docs/adr/0030) is dropped for now, not just
        # emptied of facts — an orphaned Formula binding with no DriverFact
        # data would compute as zero and silently override that leaf's real
        # fabricated GLFact value (see docs/adr/0032). Revisit once/if the
        # driver-decomposition demo is re-targeted at FOCUS_COMPANY_CODE.
        session.exec(delete(DriverFormulaTerm))
        session.exec(delete(DriverFormula))
        session.exec(delete(DriverFact))
        session.exec(delete(Driver))
        session.exec(delete(GLFact))
        session.exec(delete(GLNode))
        session.exec(delete(Period))
        session.exec(delete(CompanyNode))
        session.commit()

        session.add_all(hierarchy)
        session.add_all(periods)
        session.add_all(company_nodes)
        session.commit()

        session.add_all(facts)
        session.commit()

    print(f"Seeded {len(hierarchy)} GL/FSI nodes")
    print(f"Seeded {len(periods)} periods across {len(FISCAL_YEARS)} fiscal years ({', '.join(FISCAL_YEARS)})")
    print(f"Seeded {len(company_nodes)} company nodes ({GROUP_LABEL} + BUs + companies, 1 sampled: {FOCUS_COMPANY_CODE})")
    print(f"Seeded {len(facts)} GL facts for {FOCUS_COMPANY_CODE} across {len(FISCAL_YEARS)} years")
    print(f"Fully-modelled example node: {FULLY_MODELLED_NODE}")


if __name__ == "__main__":
    main()
