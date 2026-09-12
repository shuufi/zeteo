"""Rebuild backend/data/zeteo.db from the real GL/FSI hierarchy plus fabricated
facts for one focus company, across three real fiscal years.

Source of truth for the hierarchy is backend/seeds/master/gl_hierarchy.csv
(interior nodes) and gl_account.csv (leaves) — split from a real SAP GL/FSI
export, see docs/adr/0048. Fact amounts are fabricated with a fixed RNG seed
so the dataset is reproducible — designed (stable per-leaf cost/revenue
structure, category-level YoY growth, seasonality) rather than independently
random per row, so the P&L reads as one coherent business rather than noise.
See docs/adr/0022, 0023, 0024, 0032.

Run with: python backend/seed.py
"""

import csv
import random
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from sqlmodel import Session, SQLModel

from db import engine, init_db
from models import (
    Company,
    CompanyHierarchy,
    Driver,
    DriverFact,
    DriverFormula,
    DriverFormulaTerm,
    Financial,
    GLAccount,
    GLHierarchy,
    HierarchyKind,
    NormalBalance,
    Period,
    PeriodType,
    Source,
    VdtAccount,
    VdtHierarchy,
)
from seed_vdt import build_crew_mix_seed, build_pending_account_seed, load_vdt_hierarchy

REPO_ROOT = Path(__file__).parent.parent
GL_HIERARCHY_CSV_PATH = REPO_ROOT / "backend" / "seeds" / "master" / "gl_hierarchy.csv"
GL_ACCOUNT_CSV_PATH = REPO_ROOT / "backend" / "seeds" / "master" / "gl_account.csv"
COMPANIES_CSV_PATH = REPO_ROOT / "docs" / "misc_companies.csv"
BU_HIERARCHY_CSV_PATH = REPO_ROOT / "backend" / "seeds" / "master" / "bu_hierarchy_mapping.csv"

SEED = 42
MONTHS = range(1, 13)

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


def build_company_hierarchy() -> list[CompanyHierarchy]:
    """The BU grouping hierarchy above Company — see docs/adr/0045.
    Adjacency-list rows straight from `backend/seeds/master/bu_hierarchy_mapping.csv`
    (`code,label,parent_code,hierarchy_kind`); depth is whatever the CSV
    encodes, not a fixed number of tiers.
    """
    rows = list(csv.DictReader(BU_HIERARCHY_CSV_PATH.open(encoding="utf-8-sig")))
    order_by_parent: dict[str, int] = {}
    nodes = []
    for row in rows:
        parent_code = row["parent_code"].strip() or None
        order_by_parent[parent_code] = order_by_parent.get(parent_code, 0) + 1
        nodes.append(
            CompanyHierarchy(
                code=row["code"].strip(),
                label=row["label"].strip(),
                parent_code=parent_code,
                hierarchy_kind=HierarchyKind(row["hierarchy_kind"].strip()),
                order=order_by_parent[parent_code],
            )
        )
    return nodes


def build_company_nodes(bu_node_codes: set[str]) -> list[Company]:
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
        if bu_code not in bu_node_codes:
            raise ValueError(f"Unknown BU code {bu_code!r} in {COMPANIES_CSV_PATH}: not in {BU_HIERARCHY_CSV_PATH}")
        if company_code in seen_codes:
            raise ValueError(f"Duplicate Company Code in {COMPANIES_CSV_PATH}: {company_code}")
        seen_codes.add(company_code)
        rows_by_bu.setdefault(bu_code, []).append({**row, "Currency": currency})

    nodes = []
    for bu_code, companies in rows_by_bu.items():
        for company_order, company in enumerate(companies, start=1):
            company_code = company["Company Code"].strip()
            nodes.append(
                Company(
                    code=company_code,
                    label=company["Company Name"].strip(),
                    bu_node_code=bu_code,
                    order=company_order,
                    is_sampled=company_code == FOCUS_COMPANY_CODE,
                    currency=company["Currency"],
                )
            )
    return nodes


def sampled_company_codes(company_nodes: list[Company]) -> list[str]:
    return [n.code for n in company_nodes if n.is_sampled]


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


def load_gl_hierarchy() -> list[GLHierarchy]:
    rows = list(csv.DictReader(GL_HIERARCHY_CSV_PATH.open(encoding="utf-8-sig")))
    return [
        GLHierarchy(code=r["code"], description=r["label"], parent_code=r["parent_code"] or None)
        for r in rows
    ]


def load_gl_accounts() -> list[GLAccount]:
    rows = list(csv.DictReader(GL_ACCOUNT_CSV_PATH.open(encoding="utf-8-sig")))
    return [
        GLAccount(
            code=r["code"],
            description=r["label"],
            parent_code=r["parent_code"],
            normal_balance=NORMAL_BALANCE_BY_PREFIX[r["code"][0]],
        )
        for r in rows
    ]


def validate_gl_data(hierarchy: list[GLHierarchy], accounts: list[GLAccount]) -> None:
    """Invariants the old combined GLNode table enforced structurally
    (one shared code space, one node_type per row) that the split across
    gl_hierarchy.csv/gl_account.csv can now only violate by seed-data error —
    see docs/adr/0048's seed-time integrity checks."""
    hierarchy_codes = {n.code for n in hierarchy}
    account_codes = {n.code for n in accounts}

    overlap = hierarchy_codes & account_codes
    if overlap:
        raise ValueError(f"Duplicate codes in both gl_hierarchy.csv and gl_account.csv: {overlap}")

    roots = [n for n in hierarchy if n.parent_code is None]
    if len(roots) != 1:
        raise ValueError(f"Expected exactly one GL hierarchy root (null parent_code), found {[n.code for n in roots]}")

    for n in accounts:
        if n.parent_code not in hierarchy_codes:
            raise ValueError(f"gl_account {n.code}'s parent_code {n.parent_code!r} isn't a gl_hierarchy code (a leaf can never parent another row)")

    parent_by_code = {n.code: n.parent_code for n in hierarchy}
    for n in hierarchy:
        if n.parent_code is not None and n.parent_code not in hierarchy_codes:
            raise ValueError(f"gl_hierarchy {n.code}'s parent_code {n.parent_code!r} isn't another gl_hierarchy code")
        seen: set[str] = set()
        cur = n.code
        while cur is not None:
            if cur in seen:
                raise ValueError(f"Cycle detected in gl_hierarchy starting at {n.code}")
            seen.add(cur)
            cur = parent_by_code.get(cur)

    root_code = roots[0].code
    children_by_parent: dict[str, list[str]] = {}
    for n in hierarchy:
        if n.parent_code is not None:
            children_by_parent.setdefault(n.parent_code, []).append(n.code)
    reachable: set[str] = set()
    stack = [root_code]
    while stack:
        cur = stack.pop()
        if cur in reachable:
            continue
        reachable.add(cur)
        stack.extend(children_by_parent.get(cur, []))
    unreachable = hierarchy_codes - reachable
    if unreachable:
        raise ValueError(f"gl_hierarchy rows disconnected from root {root_code!r}: {unreachable}")


def gl_hierarchy_levels(hierarchy: list[GLHierarchy]) -> dict[str, int]:
    """Depth of each gl_hierarchy node from the root, computed by walking
    parent_code — not stored (see docs/adr/0048), needed only as the base
    case for seed_vdt.py's Activity Node level_of()."""
    parent_by_code = {n.code: n.parent_code for n in hierarchy}
    level_cache: dict[str, int] = {}

    def level_of(code: str) -> int:
        if code not in level_cache:
            parent = parent_by_code[code]
            level_cache[code] = 0 if parent is None else level_of(parent) + 1
        return level_cache[code]

    return {code: level_of(code) for code in parent_by_code}


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


def generate_gl_facts(rng: random.Random, leaves: list[GLAccount], company: str) -> list[Financial]:
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
                facts.append(Financial(code=leaf.code, company=company, period_code=period_code, source=Source.ACTUAL, amount=monthly_actual[i]))
                facts.append(Financial(code=leaf.code, company=company, period_code=period_code, source=Source.BUDGET, amount=monthly_budget[i]))
    return facts


def main() -> None:
    rng = random.Random(SEED)

    gl_hierarchy = load_gl_hierarchy()
    gl_accounts = load_gl_accounts()
    validate_gl_data(gl_hierarchy, gl_accounts)
    periods = build_periods()
    company_hierarchy = build_company_hierarchy()
    bu_node_codes = {n.code for n in company_hierarchy if n.hierarchy_kind == HierarchyKind.BU}
    company_nodes = build_company_nodes(bu_node_codes)

    facts = generate_gl_facts(rng, gl_accounts, FOCUS_COMPANY_CODE)

    # VDT hierarchy pilot — see docs/adr/0033. Structure comes from
    # backend/seeds/master/vdt_hierarchy_crew_cost.csv; `gl_level_by_code`
    # lets its VDT Hierarchy Nodes compute their own `level` from the parent
    # chain without a Hierarchy Level CSV column of their own (gl_hierarchy
    # itself doesn't store level either, see docs/adr/0048 — both compute it
    # fresh).
    gl_level_by_code = gl_hierarchy_levels(gl_hierarchy)
    gl_account_codes = {n.code for n in gl_accounts}
    vdt_hierarchy_nodes, accounts = load_vdt_hierarchy(gl_level_by_code, gl_account_codes)
    vdt_drivers, vdt_formulas, vdt_terms, vdt_facts = build_crew_mix_seed(FOCUS_COMPANY_CODE, FISCAL_YEARS)
    pending_drivers, pending_formulas, pending_terms, pending_facts = build_pending_account_seed(FOCUS_COMPANY_CODE, FISCAL_YEARS)
    vdt_drivers += pending_drivers
    vdt_formulas += pending_formulas
    vdt_terms += pending_terms
    vdt_facts += pending_facts

    # Seed is a full reproducible rebuild. Drop first so schema changes (such
    # as Company.currency and exact decimal amounts) cannot leave a stale
    # checked-in SQLite shape behind.
    SQLModel.metadata.drop_all(engine)
    init_db()
    with Session(engine) as session:
        # Driver/DriverFormula data (docs/adr/0030) previously stayed dropped
        # after ADR-0032 (an orphaned Formula binding with no DriverFact data
        # would compute as zero and silently override a leaf's real fabricated
        # Financial value) — now actually repopulated, targeting the new VDT
        # hierarchy's VDT Accounts rather than GL leaves, so
        # that risk doesn't apply here.
        session.add_all(gl_hierarchy)
        session.add_all(gl_accounts)
        session.add_all(periods)
        session.add_all(company_hierarchy)
        session.add_all(company_nodes)
        session.add_all(vdt_hierarchy_nodes)
        session.add_all(accounts)
        session.add_all(vdt_drivers)
        session.add_all(vdt_formulas)
        session.add_all(vdt_terms)
        session.commit()

        session.add_all(facts)
        session.add_all(vdt_facts)
        session.commit()

    print(f"Seeded {len(gl_hierarchy)} GL hierarchy nodes and {len(gl_accounts)} GL accounts")
    print(f"Seeded {len(periods)} periods across {len(FISCAL_YEARS)} fiscal years ({', '.join(FISCAL_YEARS)})")
    print(f"Seeded {len(company_hierarchy)} BU hierarchy nodes and {len(company_nodes)} companies (1 sampled: {FOCUS_COMPANY_CODE})")
    print(f"Seeded {len(facts)} GL facts for {FOCUS_COMPANY_CODE} across {len(FISCAL_YEARS)} years")
    print(f"Seeded {len(vdt_hierarchy_nodes)} VDT Hierarchy Nodes and {len(accounts)} VDT Accounts (VDT hierarchy pilot — docs/adr/0033)")
    print(f"Seeded {len(vdt_drivers)} Drivers / {len(vdt_formulas)} Driver Formulas for {len(accounts)} VDT Accounts")
    print(f"Fully-modelled example node: {FULLY_MODELLED_NODE}")


if __name__ == "__main__":
    main()
