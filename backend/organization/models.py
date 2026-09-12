"""Imported Company and Company Hierarchy reference entities."""

from enum import Enum
from typing import Optional

from sqlalchemy import ForeignKeyConstraint, UniqueConstraint
from sqlmodel import Field, SQLModel


class HierarchyKind(str, Enum):
    BU = "BU"
    LEGAL = "LEGAL"


class CompanyHierarchy(SQLModel, table=True):
    """An imported Company grouping node, such as a Business Unit or Legal hierarchy node."""

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
    """An imported Company leaf and its monetary display currency."""

    __tablename__ = "company"

    code: str = Field(primary_key=True)
    label: str
    bu_node_code: str = Field(foreign_key="company_hierarchy.code")
    order: int
    is_sampled: bool = False
    currency: str
