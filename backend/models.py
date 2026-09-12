"""Persistence registry for schema bootstrap and transitional imports.

Entity definitions live with their owning capability. New domain code should
import from those modules directly; importing this module registers every
SQLModel table before `SQLModel.metadata.create_all()` runs.
"""

from backend.accounting.models import Financial, GLAccount, GLHierarchy, NormalBalance, Source
from backend.calendar.models import Period, PeriodType
from backend.drivers.models import Driver, DriverFact, DriverFormula, DriverFormulaTerm, FormulaOperator, OperationalUnit
from backend.organization.models import Company, CompanyHierarchy, HierarchyKind
from backend.vdt.models import VdtAccount, VdtHierarchy

__all__ = [
    "Company",
    "CompanyHierarchy",
    "Driver",
    "DriverFact",
    "DriverFormula",
    "DriverFormulaTerm",
    "Financial",
    "FormulaOperator",
    "GLAccount",
    "GLHierarchy",
    "HierarchyKind",
    "NormalBalance",
    "OperationalUnit",
    "Period",
    "PeriodType",
    "Source",
    "VdtAccount",
    "VdtHierarchy",
]
