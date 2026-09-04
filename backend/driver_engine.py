"""Recursive Driver / Driver Formula evaluation — see docs/adr/0030.

A target (a GL Posting Account leaf or a Driver) with one or more Driver
Formulas bound to it has its value computed as the sum of those formulas
(each optionally signed); a formula's own value is a sum of sum-of-products
terms over Drivers, which may themselves be Formula-driven (recursion).

Every product/quotient is evaluated *within one company* before being
combined across companies — summing two companies' Payroll Rate and then
multiplying by their summed Crew Complement would give a meaningless
"sum of products" != "product of sums" result. Money targets (GL leaves)
reduce across companies by summing (matching gl_fact's convention); Driver
values (rates/counts/ratios, never additive the way money is) reduce by
averaging — same reasoning gl_tree.py already applies across months.

Monthly arrays throughout are 12-wide (Jan..Dec), matching gl_tree.py's
convention.
"""

from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

from sqlmodel import Session, col, select

from models import Driver, DriverFact, DriverFormula, DriverFormulaTerm, FormulaOperator
from periods import load_period_hierarchy, month_codes_of_year


class DriverCycleError(Exception):
    pass


ZERO = Decimal("0")
MONEY_QUANTUM = Decimal("0.01")


class DriverEngine:
    def __init__(self, session: Session, companies: list[str], year_code: Optional[str]):
        """`year_code` restricts DriverFact loading to one fiscal year's 12
        Month codes — without it, facts across different fiscal years would
        silently sum into the same 12-wide month-array slot (the same
        cross-year hazard docs/adr/0032 already fixed for GLFact/load_monthly;
        DriverEngine just never had live multi-year Driver data to expose it
        until now — see docs/adr/0033). `year_code=None` (e.g. no Year periods
        seeded at all yet) means no facts load, same as `companies=[]` today.
        """
        self.companies = companies
        self.driver_by_code = {d.code: d for d in session.exec(select(Driver)).all()}
        self.formula_by_code = {f.code: f for f in session.exec(select(DriverFormula)).all()}

        self.formulas_by_target: dict[str, list[DriverFormula]] = defaultdict(list)
        for formula in self.formula_by_code.values():
            self.formulas_by_target[formula.target_code].append(formula)

        terms_by_formula: dict[str, list[DriverFormulaTerm]] = defaultdict(list)
        for term in session.exec(select(DriverFormulaTerm)).all():
            terms_by_formula[term.formula_code].append(term)
        self.terms_by_formula = {
            code: sorted(terms, key=lambda t: (t.term_index, t.operand_index)) for code, terms in terms_by_formula.items()
        }

        # facts[code][company][scenario] = [12 Decimals] — kept per-company so
        # formula products are computed within one company (see module docstring).
        facts: dict[str, dict[str, dict[str, list[Decimal]]]] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(lambda: [ZERO] * 12))
        )
        if companies and year_code is not None:
            period_by_code, period_children = load_period_hierarchy(session)
            month_codes = month_codes_of_year(period_by_code, period_children, year_code)
            rows = session.exec(
                select(DriverFact.code, DriverFact.company, DriverFact.scenario, DriverFact.period_code, DriverFact.amount)
                .where(col(DriverFact.company).in_(companies))
                .where(col(DriverFact.period_code).in_(list(month_codes)))
            ).all()
            for code, company, scenario, period_code, amount in rows:
                month_index = month_codes[period_code]
                facts[code][company][scenario.value][month_index] += Decimal(str(amount))
        self.facts = facts

        self._cache: dict[tuple[str, str, str], list[Decimal]] = {}

    def is_driven(self, target_code: str) -> bool:
        return target_code in self.formulas_by_target

    def formulas_for(self, target_code: str) -> list[DriverFormula]:
        return self.formulas_by_target.get(target_code, [])

    def _driver_value_for_company(self, driver_code: str, scenario: str, company: str, visiting: frozenset) -> list[Decimal]:
        cache_key = (driver_code, scenario, company)
        if cache_key in self._cache:
            return self._cache[cache_key]
        if driver_code in visiting:
            raise DriverCycleError(f"Cycle detected evaluating driver {driver_code}")
        if driver_code in self.formulas_by_target:
            value = self._target_value_for_company(driver_code, scenario, company, visiting | {driver_code})
        else:
            value = list(self.facts.get(driver_code, {}).get(company, {}).get(scenario, [ZERO] * 12))
        self._cache[cache_key] = value
        return value

    def _target_value_for_company(self, target_code: str, scenario: str, company: str, visiting: frozenset) -> list[Decimal]:
        total = [ZERO] * 12
        for formula in self.formulas_by_target.get(target_code, []):
            formula_value = self._formula_value_for_company(formula, scenario, company, visiting)
            total = [a + formula.sign * b for a, b in zip(total, formula_value)]
        if target_code not in self.driver_by_code:
            total = [value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP) for value in total]
        return total

    def _formula_value_for_company(self, formula: DriverFormula, scenario: str, company: str, visiting: frozenset) -> list[Decimal]:
        by_term: dict[int, list[DriverFormulaTerm]] = defaultdict(list)
        for term in self.terms_by_formula.get(formula.code, []):
            by_term[term.term_index].append(term)

        total = [ZERO] * 12
        for term_ops in by_term.values():
            term_value: Optional[list[Decimal]] = None
            for op in term_ops:
                operand = self._driver_value_for_company(op.driver_code, scenario, company, visiting)
                if term_value is None:
                    term_value = operand
                elif op.operator == FormulaOperator.DIVIDE:
                    term_value = [a / b if b else ZERO for a, b in zip(term_value, operand)]
                else:
                    term_value = [a * b for a, b in zip(term_value, operand)]
            total = [a + b for a, b in zip(total, term_value or [ZERO] * 12)]
        return total

    def _reduce(self, per_company: list[list[Decimal]], average: bool) -> list[Decimal]:
        total = [ZERO] * 12
        for monthly in per_company:
            total = [a + b for a, b in zip(total, monthly)]
        if average and per_company:
            divisor = Decimal(len(per_company))
            return [v / divisor for v in total]
        return total

    def target_value(self, target_code: str, scenario: str) -> list[Decimal]:
        """Monthly values (12-wide), summed across companies — for money targets (GL leaves)."""
        per_company = [self._target_value_for_company(target_code, scenario, c, frozenset()) for c in self.companies]
        return self._reduce(per_company, average=False)

    def driver_value(self, driver_code: str, scenario: str) -> list[Decimal]:
        """Monthly values (12-wide), averaged across companies — a rate/count/ratio isn't additive like money."""
        per_company = [self._driver_value_for_company(driver_code, scenario, c, frozenset()) for c in self.companies]
        return self._reduce(per_company, average=True)

    def formula_value(self, formula: DriverFormula, scenario: str, average: bool) -> list[Decimal]:
        """A single Formula's own monthly value — averaged if it targets a Driver, summed if a GL leaf."""
        per_company = [self._formula_value_for_company(formula, scenario, c, frozenset()) for c in self.companies]
        return self._reduce(per_company, average=average)

    def expression_text(self, formula_code: str) -> str:
        """Human-readable sum-of-products text, e.g. 'Crew Complement × Rank Mix Factor + Contribution Base'."""
        by_term: dict[int, list[DriverFormulaTerm]] = defaultdict(list)
        for term in self.terms_by_formula.get(formula_code, []):
            by_term[term.term_index].append(term)

        term_strings = []
        for term_ops in by_term.values():
            parts = []
            for i, op in enumerate(term_ops):
                label = self.driver_by_code[op.driver_code].description
                parts.append(label if i == 0 else f"{op.operator.value} {label}")
            term_strings.append(" ".join(parts))
        return " + ".join(term_strings)
