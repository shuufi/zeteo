"""Zeteo-owned fiscal-calendar entities."""

from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class PeriodType(str, Enum):
    YEAR = "Year"
    QUARTER = "Quarter"
    MONTH = "Month"


class Period(SQLModel, table=True):
    """A Year, Quarter, or Month in Zeteo's fiscal calendar."""

    __tablename__ = "period"

    code: str = Field(primary_key=True)
    label: str
    parent_code: Optional[str] = Field(default=None, foreign_key="period.code")
    period_type: PeriodType
    order: int
