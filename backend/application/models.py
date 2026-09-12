"""Persisted, application-wide business settings."""

from sqlmodel import Field, SQLModel


class AppSettings(SQLModel, table=True):
    """The one global settings row shared by all Zeteo capabilities."""

    __tablename__ = "app_settings"

    id: int = Field(default=1, primary_key=True)
    current_actual_year: int | None = Field(default=None, foreign_key="year.year")
    current_actual_period: int | None = Field(default=None, foreign_key="period.period")
