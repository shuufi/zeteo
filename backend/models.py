from enum import Enum
from decimal import Decimal
from typing import Optional

from sqlalchemy import Column, ForeignKeyConstraint, Numeric, UniqueConstraint
from sqlmodel import Field, SQLModel


class NormalBalance(str, Enum):
    DEBIT = "D"
    CREDIT = "C"


class Source(str, Enum):
    ACTUAL = "actual"
    BUDGET = "budget"
    PRIOR_YEAR = "prior_year"


class PeriodType(str, Enum):
    YEAR = "Year"
    QUARTER = "Quarter"
    MONTH = "Month"


class HierarchyKind(str, Enum):
    BU = "BU"
    LEGAL = "LEGAL"


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


class GLHierarchy(SQLModel, table=True):
    """The SAP GL/FSI hierarchy's interior structure — see docs/adr/0022,
    0023, and 0048 (splits this out of the former combined `GLNode`/
    `general_ledger` table, alongside leaf-only GLAccount).

    Every row is either the single Reporting Root (`NPAT`, the only row with
    a null `parent_code`) or a Reporting Node. No `node_type`/`level` columns:
    `nodeType` ("Reporting Root" vs "Reporting Node") is derived at
    tree-build time from `parent_code IS NULL`, and real leaf depth is
    confirmed uneven (2 to 5 hops across branches) so a fixed `level` int
    would misrepresent the shape, the same reasoning docs/adr/0045 used to
    drop `level` from CompanyHierarchy. No stored `normal_balance` either —
    an interior node's balance (union of its leaves', `None` if mixed, e.g.
    Gross Profit) is computed at tree-build time, not persisted.
    """

    __tablename__ = "gl_hierarchy"

    code: str = Field(primary_key=True)
    description: str
    parent_code: Optional[str] = Field(default=None, foreign_key="gl_hierarchy.code")


class GLAccount(SQLModel, table=True):
    """A Posting GL Account leaf — see docs/adr/0022, 0023, and 0048.

    Every row here is definitionally a Posting GL Account (no `node_type`
    column — that string is synthesized at tree-build time), and always
    parents into a GLHierarchy node, never another GLAccount.
    `normal_balance` is derived from the account code's first digit
    (seed.py's NORMAL_BALANCE_BY_PREFIX) and always set — unlike the former
    combined table, a leaf's balance is never ambiguous.
    """

    __tablename__ = "gl_account"

    code: str = Field(primary_key=True)
    description: str
    parent_code: str = Field(foreign_key="gl_hierarchy.code")
    normal_balance: NormalBalance


class Period(SQLModel, table=True):
    """A position in the Year/Quarter/Month hierarchy — see docs/adr/0025.

    Only Month rows are postable (carry gl_fact rows); Year and Quarter exist
    purely to roll postable Month figures up, the same relationship Reporting
    Nodes have to Posting GL Accounts in GLHierarchy/GLAccount. `order` is 1-based position
    among siblings (Month: 1-12, Quarter: 1-4, Year: always 1) — used to index
    a node's monthly-array position without parsing the code string.
    """

    __tablename__ = "period"

    code: str = Field(primary_key=True)
    label: str
    parent_code: Optional[str] = Field(default=None, foreign_key="period.code")
    period_type: PeriodType
    order: int


class CompanyHierarchy(SQLModel, table=True):
    """A position in a company-adjacent classification hierarchy — BU today,
    Legal planned — see docs/adr/0045 (supersedes docs/adr/0028's Group/BU
    tiers inside `company`). One polymorphic self-referencing table across
    `hierarchy_kind` values rather than a table per kind. Depth is
    intentionally unconstrained (no `level` column): real BU branches reach
    MISC Group at different depths, and Legal's shape isn't yet known. The
    composite `(parent_code, hierarchy_kind)` FK keeps a node's parent within
    the same hierarchy_kind, never crossing into a different hierarchy.
    """

    __tablename__ = "company_hierarchy"
    __table_args__ = (
        UniqueConstraint("code", "hierarchy_kind"),
        ForeignKeyConstraint(
            ["parent_code", "hierarchy_kind"],
            ["company_hierarchy.code", "company_hierarchy.hierarchy_kind"],
        ),
    )

    code: str = Field(primary_key=True)
    label: str
    parent_code: Optional[str] = None
    hierarchy_kind: HierarchyKind
    order: int


class Company(SQLModel, table=True):
    """A Company leaf — see docs/adr/0045 (supersedes docs/adr/0028's
    Group/BU/Company shape). BU/Group grouping now lives in
    CompanyHierarchy; every row here is a real Company, the only level ever
    referenced by gl_fact.company. `is_sampled` marks which Companies carry
    real fake fact data (see docs/adr/0024). `bu_node_code` is required —
    BU membership was always mandatory before this change. `order` is
    1-based position among siblings, for stable display ordering. Renamed
    from `CompanyNode` — see docs/adr/0046.
    """

    __tablename__ = "company"

    code: str = Field(primary_key=True)
    label: str
    bu_node_code: str = Field(foreign_key="company_hierarchy.code")
    order: int
    is_sampled: bool = False
    currency: str


class Financial(SQLModel, table=True):
    """An actual/budget/prior-year amount for one GL account, company and Month period.
    Renamed from `GLFact` — see docs/adr/0046.
    """

    __tablename__ = "financial"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(foreign_key="gl_account.code", index=True)
    company: str = Field(foreign_key="company.code", index=True)
    period_code: str = Field(foreign_key="period.code", index=True)
    source: Source
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
    displayed_under: Optional[str] = Field(default=None, foreign_key="gl_account.code")


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
    source: Source
    # One column serves both exact two-decimal monetary rates and native-unit
    # operational measures that may need more precision.
    amount: Decimal = Field(sa_column=Column(Numeric(24, 6), nullable=False))


class DriverFormula(SQLModel, table=True):
    """A named sum-of-products expression computing exactly one target — see docs/adr/0030.

    `target_code` is either a GL Posting Account leaf (`gl_account.code`)
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


class VdtHierarchy(SQLModel, table=True):
    """A position in the VDT hierarchy's mid-tier — see docs/adr/0033.
    Renamed from `ActivityNode` — see docs/adr/0047.

    Own table rather than folding into GLHierarchy, for the same reason
    Driver got its own table in ADR-0030: gl_account's existing consumers
    (e.g. seed.py's NORMAL_BALANCE_BY_PREFIX, keyed on SAP code shape) assume
    a closed, numeric code space that V-prefixed codes would break.

    `parent_code` is deliberately NOT a declared foreign_key: it points at
    either another VdtHierarchy.code (interior nesting) or a
    gl_hierarchy.code (the top-level attachment point, e.g. PNL-0011) — a
    single column can't FK two tables. Resolved by call-site convention only,
    the same move ADR-0030 already made for DriverFormula.target_code; safe
    here too since this SQLite database never enables FK enforcement (db.py).
    """

    __tablename__ = "vdt_hierarchy"

    code: str = Field(primary_key=True)
    description: str
    parent_code: str
    level: int


class VdtAccount(SQLModel, table=True):
    """The VDT hierarchy's terminal line — see docs/adr/0033.
    Renamed from `PostingActivityAccount` — see docs/adr/0047.

    Not the same row as a Posting GL Account: its company-local-currency amount is always
    computed by its own Driver Formula (a DriverFormula.target_code equal to
    this row's `code` — a third target-code namespace that falls out of
    DriverFormula's existing untyped, call-site-resolved `target_code` for
    free), never a stored raw fact. `fa_gl_code` is a display/reconciliation
    anchor to the real GL account it's conceptually explaining — many-to-one
    allowed, and deliberately NOT required to reconcile to that account's
    real Financial total; the gap between them is what the Reconciliation report
    surfaces, not an error to close. `fa_gl_code` is always a leaf
    (`gl_account.code`), never an interior `gl_hierarchy` node — verified
    empirically (docs/adr/0048) that every FA GL value in seed data is a
    Posting GL Account.
    """

    __tablename__ = "vdt_account"

    code: str = Field(primary_key=True)
    description: str
    parent_code: str = Field(foreign_key="vdt_hierarchy.code")
    fa_gl_code: str = Field(foreign_key="gl_account.code")
