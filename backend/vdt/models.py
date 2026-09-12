"""Zeteo-owned Value Driver Tree configuration entities."""

from sqlmodel import Field, SQLModel


class VdtHierarchy(SQLModel, table=True):
    """A non-leaf VDT Hierarchy Node, attached to VDT or Accounting structure."""

    __tablename__ = "vdt_hierarchy"

    code: str = Field(primary_key=True)
    description: str
    parent_code: str
    level: int


class VdtAccount(SQLModel, table=True):
    """A VDT leaf with a display/reconciliation anchor to a Posting GL Account."""

    __tablename__ = "vdt_account"

    code: str = Field(primary_key=True)
    description: str
    parent_code: str = Field(foreign_key="vdt_hierarchy.code")
    fa_gl_code: str = Field(foreign_key="gl_account.code")
