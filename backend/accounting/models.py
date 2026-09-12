"""Imported Accounting reference entities and financial observations."""

from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlalchemy import Column, Numeric
from sqlmodel import Field, SQLModel


class NormalBalance(str, Enum):
    DEBIT = "D"
    CREDIT = "C"


class Source(str, Enum):
    ACTUAL = "actual"
    BUDGET = "budget"
    PRIOR_YEAR = "prior_year"


class GLHierarchy(SQLModel, table=True):
    """An imported Reporting Root or Reporting Node in the Accounting hierarchy."""

    __tablename__ = "gl_hierarchy"

    code: str = Field(primary_key=True)
    description: str
    parent_code: Optional[str] = Field(default=None, foreign_key="gl_hierarchy.code")


class GLAccount(SQLModel, table=True):
    """An imported Posting GL Account leaf in the Accounting hierarchy."""

    __tablename__ = "gl_account"

    code: str = Field(primary_key=True)
    description: str
    parent_code: str = Field(foreign_key="gl_hierarchy.code")
    normal_balance: NormalBalance


class Financial(SQLModel, table=True):
    """A financial amount for one imported GL account, Company, and Month."""

    __tablename__ = "financial"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(foreign_key="gl_account.code", index=True)
    company: str = Field(foreign_key="company.code", index=True)
    period_code: str = Field(foreign_key="period.code", index=True)
    source: Source
    amount: Decimal = Field(sa_column=Column(Numeric(24, 2), nullable=False))
