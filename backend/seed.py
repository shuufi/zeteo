"""Rebuild backend/data/gl.db from the real GL/FSI hierarchy plus fake facts.

Source of truth for the hierarchy is docs/anaplan_is_master_data.csv (a real
SAP GL/FSI export). Fact amounts are fabricated with a fixed RNG seed so the
dataset is reproducible. See docs/adr/0022, 0023, 0024.

Run with: python backend/seed.py
"""

import csv
import random
from pathlib import Path

from sqlmodel import Session, delete

from companies import sample_companies
from db import engine, init_db
from models import GLFact, GLNode, NodeType, NormalBalance, OperationalUnit, Scenario

REPO_ROOT = Path(__file__).parent.parent
CSV_PATH = REPO_ROOT / "docs" / "anaplan_is_master_data.csv"

SEED = 42
MONTHS = range(1, 13)

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

# Old mock's 6 curated revenue segments, remapped onto the real CSV's revenue
# Reporting Nodes (children of PNL-0002 "Revenue") — not a 1:1 name match,
# best-effort per docs/adr/0023.
OPERATIONAL_DRIVERS = [
    # (code, description, parent_code, unit, value_range)
    ("OPD-0001", "Avg. Daily Charter Rate", "PNL-0003", OperationalUnit.USD_PER_DAY, (18000, 32000)),
    ("OPD-0002", "Utilization / On-hire Rate", "PNL-0003", OperationalUnit.PERCENT, (92, 99)),
    ("OPD-0003", "Off-hire Days (fleet)", "PNL-0003", OperationalUnit.DAYS, (2, 12)),
    ("OPD-0004", "Avg. Spot/Voyage TCE Rate", "PNL-0005", OperationalUnit.USD_PER_DAY, (15000, 45000)),
    ("OPD-0005", "Spot Voyage Days (fleet)", "PNL-0005", OperationalUnit.DAYS, (10, 28)),
    ("OPD-0006", "Avg. Daily Charter Rate (Finance Lease)", "PNL-0004", OperationalUnit.USD_PER_DAY, (20000, 38000)),
    ("OPD-0007", "Fleet Uptime / Availability", "PNL-0004", OperationalUnit.PERCENT, (94, 99.5)),
    ("OPD-0008", "Avg. Project Completion Rate", "PNL-0007", OperationalUnit.PERCENT, (40, 95)),
    ("OPD-0009", "Active Projects", "PNL-0007", OperationalUnit.COUNT, (2, 9)),
    ("OPD-0010", "Demurrage Days Billed", "PNL-0006", OperationalUnit.DAYS, (5, 20)),
    ("OPD-0011", "Vessels Under Management", "PNL-0008", OperationalUnit.COUNT, (8, 25)),
    ("OPD-0012", "Avg. Fee per Vessel", "PNL-0008", OperationalUnit.USD_PER_MONTH, (12000, 28000)),
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


def load_operational_driver_nodes(hierarchy: list[GLNode]) -> list[GLNode]:
    level_by_code = {n.code: n.level for n in hierarchy}
    return [
        GLNode(
            code=code,
            description=description,
            parent_code=parent_code,
            node_type=NodeType.OPERATIONAL_DRIVER,
            level=level_by_code[parent_code] + 1,
            normal_balance=None,
            unit=unit,
        )
        for code, description, parent_code, unit, _range in OPERATIONAL_DRIVERS
    ]


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


def generate_gl_facts(rng: random.Random, leaves: list[GLNode], companies: list[dict]) -> list[GLFact]:
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
                facts.append(GLFact(code=leaf.code, company=company["code"], month=month, scenario=Scenario.ACTUAL, amount=monthly_actual[i]))
                facts.append(GLFact(code=leaf.code, company=company["code"], month=month, scenario=Scenario.BUDGET, amount=monthly_budget[i]))
                facts.append(GLFact(code=leaf.code, company=company["code"], month=month, scenario=Scenario.PRIOR_YEAR, amount=monthly_prior[i]))
    return facts


def generate_operational_facts(rng: random.Random, companies: list[dict]) -> list[GLFact]:
    facts = []
    for code, _description, _parent_code, _unit, (lo, hi) in OPERATIONAL_DRIVERS:
        for company in companies:
            base = rng.uniform(lo, hi)
            for month in MONTHS:
                drift = rng.uniform(-0.05, 0.05) * (hi - lo)
                value = min(max(base + drift * month / 12, lo), hi)
                facts.append(GLFact(code=code, company=company["code"], month=month, scenario=Scenario.ACTUAL, amount=round(value, 2)))
    return facts


def main() -> None:
    rng = random.Random(SEED)

    hierarchy = load_hierarchy_nodes()
    operational_nodes = load_operational_driver_nodes(hierarchy)
    all_nodes = hierarchy + operational_nodes

    leaves = [n for n in hierarchy if n.node_type == NodeType.POSTING_GL_ACCOUNT]
    companies = sample_companies()

    facts = generate_gl_facts(rng, leaves, companies)
    facts += generate_operational_facts(rng, companies)

    init_db()
    with Session(engine) as session:
        session.exec(delete(GLFact))
        session.exec(delete(GLNode))
        session.commit()

        session.add_all(all_nodes)
        session.commit()

        session.add_all(facts)
        session.commit()

    print(f"Seeded {len(all_nodes)} nodes ({len(hierarchy)} GL/FSI + {len(operational_nodes)} operational driver)")
    print(f"Seeded {len(facts)} facts across {len(companies)} sampled companies")
    print(f"Fully-modelled example node: {FULLY_MODELLED_NODE}")


if __name__ == "__main__":
    main()
