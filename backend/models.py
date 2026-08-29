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


class OperationalUnit(str, Enum):
    USD_PER_DAY = "usd-per-day"
    USD_PER_MONTH = "usd-per-month"
    PERCENT = "percent"
    DAYS = "days"
    COUNT = "count"


class GLNode(SQLModel, table=True):
    """A position in the SAP GL/FSI hierarchy — see docs/adr/0022 and 0023."""

    __tablename__ = "gl_node"

    code: str = Field(primary_key=True)
    description: str
    parent_code: Optional[str] = Field(default=None, foreign_key="gl_node.code")
    node_type: NodeType
    level: int
    # Only meaningful for Posting GL Account leaves (derived from the account
    # code's first digit) and for Reporting Nodes whose entire leaf subtree is
    # uniformly one category. Null for mixed subtotals (e.g. Gross Profit) and
    # for Operational Driver nodes, which never enter the financial rollup.
    normal_balance: Optional[NormalBalance] = None
    unit: Optional[OperationalUnit] = None


class GLFact(SQLModel, table=True):
    """An actual/budget/prior-year amount for one node, company and month."""

    __tablename__ = "gl_fact"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(foreign_key="gl_node.code", index=True)
    company: str = Field(index=True)
    month: int
    scenario: Scenario
    amount: float
