from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class NodeType(str, Enum):
    REPORTING_ROOT = "Reporting Root"
    REPORTING_NODE = "Reporting Node"
    POSTING_GL_ACCOUNT = "Posting GL Account"
    OPERATIONAL_DRIVER = "Operational Driver"


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
    USD_PER_DAY = "usd-per-day"
    USD_PER_MONTH = "usd-per-month"
    PERCENT = "percent"
    DAYS = "days"
    COUNT = "count"


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
    # uniformly one category. Null for mixed subtotals (e.g. Gross Profit) and
    # for Operational Driver nodes, which never enter the financial rollup.
    normal_balance: Optional[NormalBalance] = None
    unit: Optional[OperationalUnit] = None


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


class GLFact(SQLModel, table=True):
    """An actual/budget/prior-year amount for one node, company and Month period."""

    __tablename__ = "financial"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(foreign_key="general_ledger.code", index=True)
    company: str = Field(foreign_key="company.code", index=True)
    period_code: str = Field(foreign_key="period.code", index=True)
    scenario: Scenario
    amount: float
