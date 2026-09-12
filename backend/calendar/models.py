"""Zeteo-owned fiscal-calendar entities — see docs/adr/0051."""

from sqlmodel import Field, SQLModel


class Year(SQLModel, table=True):
    """A fiscal year Zeteo knows about (e.g. 2026). Calendar-aligned today,
    but that alignment is configuration, not part of the term itself."""

    __tablename__ = "year"

    year: int = Field(primary_key=True)


class Period(SQLModel, table=True):
    """A fiscal-relative posting period, 1-12 (period 1 is a fiscal year's
    first month, not necessarily January). Static reference data — one row
    per period number, shared by every fiscal Year, not seeded per-year.
    Quarter is stored here rather than derived, since it's a fixed property
    of the period number (1-3 -> Q1, 4-6 -> Q2, ...)."""

    __tablename__ = "period"

    period: int = Field(primary_key=True)
    label: str
    quarter: int
