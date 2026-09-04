"""Builds the VDT (activity-based) hierarchy's pilot seed data — see docs/adr/0033.

Source of truth for structure is docs/vdt-hierarchy-crew-cost.csv (Activity
Node / Posting Activity Account rows, reusing real GL codes as `FA GL`
anchors). Driver/DriverFormula content for the first 3 of 21 Posting Activity
Accounts (VA00000001-3) is hand-authored here rather than a second CSV — 21
rows is too small a dataset to justify more ad-hoc CSV machinery, and this
follows diagnostic_content.py's existing precedent for hand-curated content.
The remaining ~18 accounts have no Driver Formula bound yet (fall back to
zero — see vdt_tree.py's warning) until their content is provided, a
follow-up, lower-risk content-only change once this shape is validated.

Pure builder module, no session/DB access — mirrors seed.py's own
build_periods()/build_company_nodes() style: called from seed.py:main() after
the GL hierarchy is loaded (for `gl_level_by_code`) and before that module's
own delete+add_all+commit sequence.
"""

import csv
import random
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from models import (
    ActivityNode,
    Driver,
    DriverFact,
    DriverFormula,
    DriverFormulaTerm,
    FormulaOperator,
    OperationalUnit,
    PostingActivityAccount,
    Scenario,
)

REPO_ROOT = Path(__file__).parent.parent
CSV_PATH = REPO_ROOT / "docs" / "vdt-hierarchy-crew-cost.csv"

SEED = 4300


def load_activity_hierarchy(gl_level_by_code: dict[str, int]) -> tuple[list[ActivityNode], list[PostingActivityAccount]]:
    """Reads docs/vdt-hierarchy-crew-cost.csv, splitting rows by Node Type.

    `level` isn't a CSV column here (unlike anaplan_is_master_data.csv) — computed
    from the parent chain, terminating either at a known GL code's own level
    or recursing into another Activity Node row. Every `FA GL` value must
    resolve to an already-seeded general_ledger code — fail loud on a typo
    rather than silently seeding an orphaned anchor.
    """
    rows = list(csv.DictReader(CSV_PATH.open(encoding="utf-8-sig")))
    by_code = {r["Code"]: r for r in rows}
    level_cache: dict[str, int] = {}

    def level_of(code: str) -> int:
        if code in level_cache:
            return level_cache[code]
        parent_code = by_code[code]["Parent Code"]
        if parent_code in gl_level_by_code:
            level = gl_level_by_code[parent_code] + 1
        else:
            level = level_of(parent_code) + 1
        level_cache[code] = level
        return level

    activity_nodes: list[ActivityNode] = []
    accounts: list[PostingActivityAccount] = []
    for r in rows:
        code, node_type = r["Code"], r["Node Type"]
        if node_type == "Activity Node":
            activity_nodes.append(ActivityNode(code=code, description=r["Description"], parent_code=r["Parent Code"], level=level_of(code)))
        elif node_type == "Posting Activity Account":
            fa_gl_code = r["FA GL"]
            if fa_gl_code not in gl_level_by_code:
                raise ValueError(f"{code}'s FA GL {fa_gl_code!r} doesn't match any seeded general_ledger code")
            accounts.append(PostingActivityAccount(code=code, description=r["Description"], parent_code=r["Parent Code"], fa_gl_code=fa_gl_code))
        else:
            raise ValueError(f"Unknown Node Type {node_type!r} for {code}")

    return activity_nodes, accounts


# First 3 of 21 Posting Activity Accounts get real Driver Formula content —
# enough to prove the pipeline end-to-end (seed -> DriverEngine -> vdt_tree ->
# API -> frontend render); the rest are a follow-up content-only change once
# this shape is validated (see docs/adr/0033's Open Items). Each entry:
# target VA code, (headcount driver code/description/base count/YoY growth),
# (rate driver code/description/base local-currency-per-month/YoY growth) —
# the product lands directly in absolute local currency, no further scaling (a formula author is
# trusted to combine drivers whose product already lands in the target's
# unit — see docs/adr/0030).
_CREW_MIX_FORMULAS = [
    (
        "VA00000001",
        ("DRV-CREWMIX-SR-HC", "Senior Officer Headcount", 8, 0.03),
        ("DRV-CREWMIX-SR-RATE", "Average Salary Rate - Senior Officer", 18_000.00, 0.04),
    ),
    (
        "VA00000002",
        ("DRV-CREWMIX-JR-HC", "Junior Officer Headcount", 15, 0.03),
        ("DRV-CREWMIX-JR-RATE", "Average Salary Rate - Junior Officer", 10_000.00, 0.04),
    ),
    (
        "VA00000003",
        ("DRV-CREWMIX-RT-HC", "Ratings/Crew Headcount", 40, 0.02),
        ("DRV-CREWMIX-RT-RATE", "Average Salary Rate - Ratings/Crew", 6_000.00, 0.04),
    ),
]

# Deliberate within-year drift so adjacent months (e.g. Aug vs Sep) show a
# legible movement in VDT Statement's comparison bridge — see docs/adr/0034.
# Before this, only hc_growth/rate_growth (year-over-year) existed and every
# month within a year was flat (annual base plus pure noise), so a "vs This
# Year" comparison of two arbitrary months barely moved. Centered on month
# 6.5 (mid-year) so the annual average stays close to hc_base/rate_annual,
# same as before this change — only the within-year shape changed, not the
# year's overall level. Sized well above the noise bands below (±0.5%/±0.3%)
# so a single-month step reads clearly instead of getting lost in noise.
_MONTHLY_HC_GROWTH = 0.02
_MONTHLY_RATE_GROWTH = 0.015


def _decimal(value: float, places: str) -> Decimal:
    return Decimal(str(value)).quantize(Decimal(places), rounding=ROUND_HALF_UP)


def build_crew_mix_seed(
    focus_company: str, fiscal_years: list[str]
) -> tuple[list[Driver], list[DriverFormula], list[DriverFormulaTerm], list[DriverFact]]:
    """Rates differ by rank, so each rank gets its own Driver row rather than
    sharing one 'average salary rate' — a Driver carries exactly one value
    per period, so a differing-by-rank rate can't be a single shared row.
    """
    rng = random.Random(SEED)
    drivers: list[Driver] = []
    formulas: list[DriverFormula] = []
    terms: list[DriverFormulaTerm] = []
    facts: list[DriverFact] = []

    for target_code, (hc_code, hc_desc, hc_base, hc_growth), (rate_code, rate_desc, rate_base, rate_growth) in _CREW_MIX_FORMULAS:
        drivers.append(Driver(code=hc_code, description=hc_desc, unit=OperationalUnit.COUNT))
        drivers.append(Driver(code=rate_code, description=rate_desc, unit=OperationalUnit.CURRENCY_PER_MONTH))

        formula_code = f"FORMULA-{target_code}"
        formulas.append(DriverFormula(code=formula_code, description=f"{hc_desc} x {rate_desc}", target_code=target_code, sign=1))
        terms.append(
            DriverFormulaTerm(formula_code=formula_code, term_index=0, operand_index=0, driver_code=hc_code, operator=FormulaOperator.MULTIPLY)
        )
        terms.append(
            DriverFormulaTerm(formula_code=formula_code, term_index=0, operand_index=1, driver_code=rate_code, operator=FormulaOperator.MULTIPLY)
        )

        for year_index, fiscal_year in enumerate(fiscal_years):
            hc_annual = hc_base * ((1 + hc_growth) ** year_index)
            rate_annual = rate_base * ((1 + rate_growth) ** year_index)
            for month in range(1, 13):
                period_code = f"{fiscal_year}-M{month:02d}"
                hc_month = hc_annual * ((1 + _MONTHLY_HC_GROWTH) ** (month - 6.5))
                rate_month = rate_annual * ((1 + _MONTHLY_RATE_GROWTH) ** (month - 6.5))
                facts.append(
                    DriverFact(
                        code=hc_code,
                        company=focus_company,
                        period_code=period_code,
                        scenario=Scenario.ACTUAL,
                        amount=_decimal(hc_month * rng.uniform(0.995, 1.005), "0.001"),
                    )
                )
                facts.append(
                    DriverFact(
                        code=hc_code,
                        company=focus_company,
                        period_code=period_code,
                        scenario=Scenario.BUDGET,
                        amount=_decimal(hc_month * rng.uniform(0.995, 1.005), "0.001"),
                    )
                )
                facts.append(
                    DriverFact(
                        code=rate_code,
                        company=focus_company,
                        period_code=period_code,
                        scenario=Scenario.ACTUAL,
                        amount=_decimal(rate_month * rng.uniform(0.997, 1.003), "0.01"),
                    )
                )
                facts.append(
                    DriverFact(
                        code=rate_code,
                        company=focus_company,
                        period_code=period_code,
                        scenario=Scenario.BUDGET,
                        amount=_decimal(rate_month * rng.uniform(0.997, 1.003), "0.01"),
                    )
                )

    return drivers, formulas, terms, facts
