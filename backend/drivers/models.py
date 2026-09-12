"""Zeteo-owned Driver configuration and observations."""

from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlalchemy import Column, Numeric
from sqlmodel import Field, SQLModel

from backend.accounting.models import Source


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


class Driver(SQLModel, table=True):
    """A reusable operational quantity that can feed one or more Driver Formulas."""

    __tablename__ = "driver"

    code: str = Field(primary_key=True)
    description: str
    unit: OperationalUnit
    displayed_under: Optional[str] = Field(default=None, foreign_key="gl_account.code")


class DriverFact(SQLModel, table=True):
    """A sourced value for a terminal Driver, Company, and Month."""

    __tablename__ = "driver_fact"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(foreign_key="driver.code", index=True)
    company: str = Field(foreign_key="company.code", index=True)
    period_code: str = Field(foreign_key="period.code", index=True)
    source: Source
    amount: Decimal = Field(sa_column=Column(Numeric(24, 6), nullable=False))


class DriverFormula(SQLModel, table=True):
    """A sum-of-products expression that computes one Driver, GL Account, or VDT Account."""

    __tablename__ = "driver_formula"

    code: str = Field(primary_key=True)
    description: str
    target_code: str
    sign: int = 1


class DriverFormulaTerm(SQLModel, table=True):
    """An ordered Driver operand within a Driver Formula term."""

    __tablename__ = "driver_formula_term"

    id: Optional[int] = Field(default=None, primary_key=True)
    formula_code: str = Field(foreign_key="driver_formula.code", index=True)
    term_index: int
    operand_index: int
    driver_code: str = Field(foreign_key="driver.code")
    operator: FormulaOperator = FormulaOperator.MULTIPLY
