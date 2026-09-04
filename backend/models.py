from enum import Enum
from decimal import Decimal
from typing import Optional

from sqlalchemy import Column, Numeric
from sqlmodel import Field, SQLModel


class NodeType(str, Enum):
    REPORTING_ROOT = "Reporting Root"
    REPORTING_NODE = "Reporting Node"
    POSTING_GL_ACCOUNT = "Posting GL Account"


class NormalBalance(str, Enum):
    DEBIT = "D"
    CREDIT = "C"


class Scenario(str, Enum):
    ACTUAL = "actual"
    BUDGET = "budget"
    PRIOR_YEAR = "prior_year"


class PeriodType(str, Enum):
    YEAR = "Year"
    QUARTER = "Quarter"
    MONTH = "Month"


class CompanyNodeType(str, Enum):
    GROUP = "Group"
    BUSINESS_UNIT = "Business Unit"
    COMPANY = "Company"


class OperationalUnit(str, Enum):
    CURRENCY_PER_DAY = "currency-per-day"
    CURRENCY_PER_MONTH = "currency-per-month"
    PERCENT = "percent"
    DAYS = "days"
    COUNT = "count"
    RATIO = "ratio"


class FormulaOperator(str, Enum):
    MULTIPLY = "×"
    DIVIDE = "÷"


class GLNode(SQLModel, table=True):
    """A position in the SAP GL/FSI hierarchy — see docs/adr/0022 and 0023."""

    __tablename__ = "general_ledger"

    code: str = Field(primary_key=True)
    description: str
    parent_code: Optional[str] = Field(default=None, foreign_key="general_ledger.code")
    node_type: NodeType
    level: int
    # Only meaningful for Posting GL Account leaves (derived from the account
    # code's first digit) and for Reporting Nodes whose entire leaf subtree is
    # uniformly one category. Null for mixed subtotals (e.g. Gross Profit).
    normal_balance: Optional[NormalBalance] = None


class Period(SQLModel, table=True):
    """A position in the Year/Quarter/Month hierarchy — see docs/adr/0025.

    Only Month rows are postable (carry gl_fact rows); Year and Quarter exist
    purely to roll postable Month figures up, the same relationship Reporting
    Nodes have to Posting GL Accounts in GLNode. `order` is 1-based position
    among siblings (Month: 1-12, Quarter: 1-4, Year: always 1) — used to index
    a node's monthly-array position without parsing the code string.
    """

    __tablename__ = "period"

    code: str = Field(primary_key=True)
    label: str
    parent_code: Optional[str] = Field(default=None, foreign_key="period.code")
    period_type: PeriodType
    order: int


class CompanyNode(SQLModel, table=True):
    """A position in the MISC Group -> Business Unit -> Company hierarchy — see docs/adr/0028.

    Mirrors GLNode/Period's adjacency-list shape. Only Company rows are ever
    referenced by gl_fact.company; `is_sampled` marks which Companies carry
    real fake fact data (see docs/adr/0024) — Group and Business Unit rows
    are pure rollup groupings, the same relationship Year/Quarter have to
    Month in the period hierarchy. `order` is 1-based position among
    siblings, for stable display ordering.
    """

    __tablename__ = "company"

    code: str = Field(primary_key=True)
    label: str
    parent_code: Optional[str] = Field(default=None, foreign_key="company.code")
    node_type: CompanyNodeType
    order: int
    is_sampled: bool = False
    # Required for Company leaves; null for the Group/BU grouping rows.
    currency: Optional[str] = None


class GLFact(SQLModel, table=True):
    """An actual/budget/prior-year amount for one node, company and Month period."""

    __tablename__ = "financial"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(foreign_key="general_ledger.code", index=True)
    company: str = Field(foreign_key="company.code", index=True)
    period_code: str = Field(foreign_key="period.code", index=True)
    scenario: Scenario
    amount: Decimal = Field(sa_column=Column(Numeric(24, 2), nullable=False))


class Driver(SQLModel, table=True):
    """A reusable named quantity (e.g. Crew Complement, Payroll Rate) — see docs/adr/0030.

    Lives outside the GL/FSI hierarchy entirely: no `parent_code`, no fixed
    tree position — the same Driver can feed multiple Driver Formulas as a
    term, or be the target of Driver Formulas itself (see DriverFormula),
    which is what lets driver decomposition recurse. `displayed_under` is a
    display-only anchor to a GL leaf, used only by drivers with no Formula
    and no reference as anyone's term (e.g. the legacy charter-rate/
    utilization drivers) — never part of the compute graph.
    """

    __tablename__ = "driver"

    code: str = Field(primary_key=True)
    description: str
    unit: OperationalUnit
    displayed_under: Optional[str] = Field(default=None, foreign_key="general_ledger.code")


class DriverFact(SQLModel, table=True):
    """An actual/budget/prior-year value for one Driver, company and Month period.

    Only present for terminal Drivers (no Formula bound to them as target) —
    a Formula-driven Driver's value is always computed, never stored.
    """

    __tablename__ = "driver_fact"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(foreign_key="driver.code", index=True)
    company: str = Field(foreign_key="company.code", index=True)
    period_code: str = Field(foreign_key="period.code", index=True)
    scenario: Scenario
    # One column serves both exact two-decimal monetary rates and native-unit
    # operational measures that may need more precision.
    amount: Decimal = Field(sa_column=Column(Numeric(24, 6), nullable=False))


class DriverFormula(SQLModel, table=True):
    """A named sum-of-products expression computing exactly one target — see docs/adr/0030.

    `target_code` is either a GL Posting Account leaf (`general_ledger.code`)
    or another Driver (`driver.code`) — no single-table FK is possible since
    it's polymorphic, but the two code spaces never collide (SAP GL codes vs
    `DRV-`/`OPD-` codes). Multiple formulas may share a target; the target's
    value is the sum of every formula bound to it, each scaled by `sign`.
    """

    __tablename__ = "driver_formula"

    code: str = Field(primary_key=True)
    description: str
    target_code: str
    sign: int = 1


class DriverFormulaTerm(SQLModel, table=True):
    """One operand within a Driver Formula's sum-of-products expression.

    `term_index` groups operands into the additive terms of the formula
    (term values are summed); `operand_index` orders operands within a term,
    combined left-to-right by `operator` (ignored on the first operand of a
    term, which just seeds the running product/quotient).
    """

    __tablename__ = "driver_formula_term"

    id: Optional[int] = Field(default=None, primary_key=True)
    formula_code: str = Field(foreign_key="driver_formula.code", index=True)
    term_index: int
    operand_index: int
    driver_code: str = Field(foreign_key="driver.code")
    operator: FormulaOperator = FormulaOperator.MULTIPLY


class ActivityNode(SQLModel, table=True):
    """A position in the VDT (activity-based) hierarchy's mid-tier — see docs/adr/0033.

    Own table rather than a new GLNode.node_type value, for the same reason
    Driver got its own table in ADR-0030: general_ledger's existing consumers
    (e.g. seed.py's NORMAL_BALANCE_BY_PREFIX, keyed on SAP code shape) assume
    a closed, numeric-or-PNL-/NPAT code space that V-prefixed codes would break.

    `parent_code` is deliberately NOT a declared foreign_key: it points at
    either another ActivityNode.code (interior nesting) or a
    general_ledger.code (the top-level attachment point, e.g. PNL-0011) — a
    single column can't FK two tables. Resolved by call-site convention only,
    the same move ADR-0030 already made for DriverFormula.target_code; safe
    here too since this SQLite database never enables FK enforcement (db.py).
    """

    __tablename__ = "activity_node"

    code: str = Field(primary_key=True)
    description: str
    parent_code: str
    level: int


class PostingActivityAccount(SQLModel, table=True):
    """The VDT hierarchy's terminal line — see docs/adr/0033.

    Not the same row as a Posting GL Account: its company-local-currency amount is always
    computed by its own Driver Formula (a DriverFormula.target_code equal to
    this row's `code` — a third target-code namespace that falls out of
    DriverFormula's existing untyped, call-site-resolved `target_code` for
    free), never a stored raw fact. `fa_gl_code` is a display/reconciliation
    anchor to the real GL account it's conceptually explaining — many-to-one
    allowed, and deliberately NOT required to reconcile to that account's
    real GLFact total; the gap between them is what the Reconciliation report
    surfaces, not an error to close.
    """

    __tablename__ = "posting_activity_account"

    code: str = Field(primary_key=True)
    description: str
    parent_code: str = Field(foreign_key="activity_node.code")
    fa_gl_code: str = Field(foreign_key="general_ledger.code")
