"""Builds the VDT (activity-based) hierarchy's pilot seed data — see docs/adr/0033.

Source of truth for structure is docs/vdt-hierarchy-crew-cost.csv (Activity
Node / Posting Activity Account rows, reusing real GL codes as `FA GL`
anchors). Driver/DriverFormula content for all 21 Posting Activity Accounts
is hand-authored here rather than a second CSV — 21 rows is too small a
dataset to justify more ad-hoc CSV machinery, and this follows
diagnostic_content.py's existing precedent for hand-curated content.
VA00000001-3 (_CREW_MIX_FORMULAS, fixed headcount x rate shape) proved the
pipeline end-to-end first; VA00000004-021 (_PENDING_ACCOUNT_FORMULAS,
general sum-of-products shape) followed once that shape was validated — see
docs/adr/0036.

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


# The remaining 18 of 21 Posting Activity Accounts (VA00000004-021), sourced
# from docs/vdt-hierarchy-crew-cost.csv's own Formula column rather than
# hand-derived like _CREW_MIX_FORMULAS above. Unlike that fixed
# headcount-times-rate shape, formulas here vary (single-operand lump sum,
# shared drivers across accounts), so each entry is a general
# (target, description, sign, terms) tuple — `terms` is a list of additive
# terms, each itself a list of (driver_code, description, unit, base, YoY
# growth) operands chained by multiplication left-to-right (none of these 18
# need division). `no_of_movements` is the same physical crew-movement count
# behind airfare, transport, agency fee and joining admin fee, so those four
# formulas deliberately reuse one driver (DRV-CREWMOVE-COUNT) rather than
# four independent ones — see docs/adr/0036.
_PENDING_ACCOUNT_FORMULAS = [
    (
        "VA00000004",
        "Allowance Entitlement Count x Average Allowance Rate",
        1,
        [[("DRV-ALLOW-QTY", "Allowance Entitlement Count", OperationalUnit.COUNT, 50, 0.02),
          ("DRV-ALLOW-RATE", "Average Allowance Rate", OperationalUnit.CURRENCY_PER_MONTH, 500.00, 0.03)]],
    ),
    (
        "VA00000005",
        "Aggregate Monthly Salary Base x Leave Accrual Factor",
        1,
        [[("DRV-LEAVE-SALARYBASE", "Aggregate Monthly Salary Base (Leave Accrual)", OperationalUnit.CURRENCY_PER_MONTH, 350_000.00, 0.03),
          ("DRV-LEAVE-FACTOR", "Leave Accrual Factor", OperationalUnit.PERCENT, 0.083, 0.0)]],
    ),
    (
        "VA00000006",
        "Overtime Hours x Overtime Hourly Rate",
        1,
        [[("DRV-OT-HOURS", "Overtime Hours", OperationalUnit.COUNT, 200, 0.02),
          ("DRV-OT-RATE", "Overtime Hourly Rate", OperationalUnit.CURRENCY_PER_MONTH, 45.00, 0.03)]],
    ),
    (
        "VA00000007",
        "Eligible Crew Count x Bonus per Crew",
        1,
        [[("DRV-BONUS-ELIGCREW", "Eligible Crew Count (Bonus)", OperationalUnit.COUNT, 55, 0.02),
          ("DRV-BONUS-PERCREW", "Bonus per Crew", OperationalUnit.CURRENCY_PER_MONTH, 800.00, 0.03)]],
    ),
    (
        "VA00000008",
        "Eligible Payroll Base x EPF Contribution Rate",
        1,
        [[("DRV-EPF-PAYROLLBASE", "Eligible Payroll Base", OperationalUnit.CURRENCY_PER_MONTH, 400_000.00, 0.03),
          ("DRV-EPF-RATE", "EPF Contribution Rate", OperationalUnit.PERCENT, 0.13, 0.0)]],
    ),
    (
        "VA00000009",
        "Crew Movement Count x Weighted Average Airfare",
        1,
        [[("DRV-CREWMOVE-COUNT", "Crew Movement Count", OperationalUnit.COUNT, 12, 0.02),
          ("DRV-AIRFARE-AVGCOST", "Weighted Average Airfare", OperationalUnit.CURRENCY_PER_MONTH, 3_500.00, 0.04)]],
    ),
    (
        "VA00000010",
        "Crew Movement Count x Weighted Transport Cost",
        1,
        [[("DRV-CREWMOVE-COUNT", "Crew Movement Count", OperationalUnit.COUNT, 12, 0.02),
          ("DRV-TRANSPORT-COST", "Weighted Transport Cost", OperationalUnit.CURRENCY_PER_MONTH, 900.00, 0.03)]],
    ),
    (
        "VA00000011",
        "Room Nights x Average Hotel Rate",
        1,
        [[("DRV-ACCOM-ROOMNIGHTS", "Room Nights", OperationalUnit.DAYS, 90, 0.02),
          ("DRV-ACCOM-RATE", "Average Hotel Rate", OperationalUnit.CURRENCY_PER_DAY, 250.00, 0.03)]],
    ),
    (
        "VA00000012",
        "Crew Movement Count x Average Agency/Port Handling Fee",
        1,
        [[("DRV-CREWMOVE-COUNT", "Crew Movement Count", OperationalUnit.COUNT, 12, 0.02),
          ("DRV-AGENCY-FEE", "Average Agency/Port Handling Fee", OperationalUnit.CURRENCY_PER_MONTH, 600.00, 0.03)]],
    ),
    (
        "VA00000013",
        "Onboard Crew Count x Monthly Victualling Rate",
        1,
        [[("DRV-VICT-CREW", "Onboard Crew Count (Victualling)", OperationalUnit.COUNT, 22, 0.01),
          ("DRV-VICT-RATE", "Monthly Victualling Rate per Crew", OperationalUnit.CURRENCY_PER_MONTH, 900.00, 0.03)]],
    ),
    (
        "VA00000014",
        "Extra Meals/Freight/Holiday Provision",
        1,
        # CSV names this "annual_lump_sum", but every Driver is valued per
        # company x month (ADR-0030) — base value here is the monthly
        # equivalent (annual budget / 12), not the annual figure itself.
        [[("DRV-VICT-LUMPSUM", "Extra Meals/Freight/Holiday Provision", OperationalUnit.CURRENCY_PER_MONTH, 15_000.00, 0.02)]],
    ),
    (
        "VA00000015",
        "Medical Check-up Count x Average Medical Check-up Rate",
        1,
        [[("DRV-MEDCHECK-COUNT", "Medical Check-up Count", OperationalUnit.COUNT, 6, 0.01),
          ("DRV-MEDCHECK-RATE", "Average Medical Check-up Rate", OperationalUnit.CURRENCY_PER_MONTH, 350.00, 0.03)]],
    ),
    (
        "VA00000016",
        "Sickness/Injury Case Count x Average Cost per Case",
        1,
        [[("DRV-SICKINJ-CASES", "Sickness/Injury Case Count", OperationalUnit.COUNT, 3, 0.01),
          ("DRV-SICKINJ-COST", "Average Cost per Sickness/Injury Case", OperationalUnit.CURRENCY_PER_MONTH, 2_500.00, 0.03)]],
    ),
    (
        "VA00000017",
        "Manning Agency Crew Count x Manning Fee per Crew",
        1,
        [[("DRV-MANNING-CREW", "Manning Agency Crew Count", OperationalUnit.COUNT, 55, 0.02),
          ("DRV-MANNING-FEE", "Manning Fee per Crew per Month", OperationalUnit.CURRENCY_PER_MONTH, 150.00, 0.03)]],
    ),
    (
        "VA00000018",
        "Crew Movement Count x Joining Admin Fee",
        1,
        [[("DRV-CREWMOVE-COUNT", "Crew Movement Count", OperationalUnit.COUNT, 12, 0.02),
          ("DRV-JOINADMIN-FEE", "Joining Admin Fee per Movement", OperationalUnit.CURRENCY_PER_MONTH, 200.00, 0.03)]],
    ),
    (
        "VA00000019",
        "Insured Crew Count x Insurance Premium per Crew",
        1,
        [[("DRV-INSURE-CREW", "Insured Crew Count", OperationalUnit.COUNT, 60, 0.02),
          ("DRV-INSURE-PREMIUM", "Insurance Premium per Crew", OperationalUnit.CURRENCY_PER_MONTH, 120.00, 0.03)]],
    ),
    (
        "VA00000020",
        "Union-Eligible Crew Count x Union Fee per Crew",
        1,
        [[("DRV-UNION-CREW", "Union-Eligible Crew Count", OperationalUnit.COUNT, 40, 0.01),
          ("DRV-UNION-FEE", "Union Fee per Crew", OperationalUnit.CURRENCY_PER_MONTH, 80.00, 0.02)]],
    ),
    (
        "VA00000021",
        "New Hires Count x Recruitment Cost per Hire",
        1,
        [[("DRV-RECRUIT-HIRES", "New Hires Count", OperationalUnit.COUNT, 4, 0.02),
          ("DRV-RECRUIT-COST", "Recruitment Cost per Hire", OperationalUnit.CURRENCY_PER_MONTH, 3_000.00, 0.03)]],
    ),
]

# Same within-year drift concept as _MONTHLY_HC_GROWTH/_MONTHLY_RATE_GROWTH
# above, generalized by unit kind rather than hardcoded headcount/rate roles,
# since these 18 formulas mix counts, currency rates and stable ratios
# (leave/EPF) that shouldn't drift or jitter the same way a headcount or a
# salary rate does.
_QUANTITY_UNITS = {OperationalUnit.COUNT, OperationalUnit.DAYS}
_RATE_UNITS = {OperationalUnit.CURRENCY_PER_MONTH, OperationalUnit.CURRENCY_PER_DAY}


def _drift_params(unit: OperationalUnit) -> tuple[float, tuple[float, float], str]:
    """(monthly within-year growth, noise multiplier range, rounding places) for a Driver's unit."""
    if unit in _QUANTITY_UNITS:
        return _MONTHLY_HC_GROWTH, (0.995, 1.005), "0.001"
    if unit in _RATE_UNITS:
        return _MONTHLY_RATE_GROWTH, (0.997, 1.003), "0.01"
    # PERCENT/RATIO: statutory or administrative ratios (EPF rate, leave
    # accrual factor) — flat within the year, only a tight noise band.
    return 0.0, (0.999, 1.001), "0.0001"


def build_pending_account_seed(
    focus_company: str, fiscal_years: list[str]
) -> tuple[list[Driver], list[DriverFormula], list[DriverFormulaTerm], list[DriverFact]]:
    """VA00000004-021's Driver Formulas — see _PENDING_ACCOUNT_FORMULAS above.

    A separate rng stream (SEED + 1) from build_crew_mix_seed keeps the two
    functions' outputs independent of call order. Drivers are deduped by
    code (DRV-CREWMOVE-COUNT is shared by four formulas) so it gets exactly
    one Driver row and one set of monthly DriverFact rows, not four
    conflicting copies.
    """
    rng = random.Random(SEED + 1)
    driver_specs: dict[str, tuple[str, OperationalUnit, float, float]] = {}
    formulas: list[DriverFormula] = []
    terms: list[DriverFormulaTerm] = []
    facts: list[DriverFact] = []

    for target_code, description, sign, term_specs in _PENDING_ACCOUNT_FORMULAS:
        formula_code = f"FORMULA-{target_code}"
        formulas.append(DriverFormula(code=formula_code, description=description, target_code=target_code, sign=sign))
        for term_index, operands in enumerate(term_specs):
            for operand_index, (driver_code, driver_desc, unit, base, growth) in enumerate(operands):
                spec = (driver_desc, unit, base, growth)
                existing = driver_specs.get(driver_code)
                if existing is not None and existing != spec:
                    raise ValueError(f"shared driver {driver_code} has conflicting specs: {existing} vs {spec}")
                driver_specs[driver_code] = spec
                terms.append(
                    DriverFormulaTerm(
                        formula_code=formula_code, term_index=term_index, operand_index=operand_index, driver_code=driver_code, operator=FormulaOperator.MULTIPLY
                    )
                )

    drivers = [Driver(code=code, description=desc, unit=unit) for code, (desc, unit, _, _) in driver_specs.items()]

    for driver_code, (_, unit, base, growth) in driver_specs.items():
        monthly_growth, noise_range, places = _drift_params(unit)
        for year_index, fiscal_year in enumerate(fiscal_years):
            annual = base * ((1 + growth) ** year_index)
            for month in range(1, 13):
                period_code = f"{fiscal_year}-M{month:02d}"
                month_value = annual * ((1 + monthly_growth) ** (month - 6.5))
                for scenario in (Scenario.ACTUAL, Scenario.BUDGET):
                    facts.append(
                        DriverFact(
                            code=driver_code,
                            company=focus_company,
                            period_code=period_code,
                            scenario=scenario,
                            amount=_decimal(month_value * rng.uniform(*noise_range), places),
                        )
                    )

    return drivers, formulas, terms, facts
