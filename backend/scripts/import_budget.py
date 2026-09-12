"""CLI entry point for the POC Budget-import contract in ADR-0049."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sqlmodel import Session

from backend.accounting.fact_import import FactImportError, apply_fact_import, validate_budget_csv
from backend.infrastructure.db import engine


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate or apply a POC budget CSV import.")
    parser.add_argument("--year", required=True, type=int, help="Four-digit calendar year, for example 2026")
    parser.add_argument("--type", choices=("financial", "driver"), required=True, dest="dataset_type")
    parser.add_argument("--file", required=True, type=Path, dest="file_path")
    parser.add_argument("--dry-run", action="store_true", help="Validate and print the replacement summary without writing (the default).")
    parser.add_argument("--apply", action="store_true", help="After confirmation, replace the selected FY + type budget facts.")
    args = parser.parse_args()

    if args.dry_run and args.apply:
        parser.error("--dry-run and --apply cannot be used together")
    if not args.file_path.is_file():
        parser.error(f"CSV file not found: {args.file_path}")

    with Session(engine) as session, args.file_path.open(newline="", encoding="utf-8-sig") as stream:
        try:
            plan = validate_budget_csv(session, args.year, args.dataset_type, stream)
        except FactImportError as error:
            for message in error.errors:
                print(f"error: {message}", file=sys.stderr)
            return 2

        print(
            f"Validated {len(plan.rows)} {plan.dataset_type} Budget rows for {plan.scope_label}; "
            f"skipped {plan.skipped_row_count} rows outside the selected year. Applying will replace "
            f"{plan.existing_fact_count} existing Budget rows in that scope.",
        )
        if not args.apply:
            print("Dry run only; no database changes were made.")
            return 0

        confirmation = input(f"Replace {plan.scope_label} facts? [y/N] ")
        if confirmation.strip().lower() not in {"y", "yes"}:
            print("Cancelled; no database changes were made.")
            return 0

        apply_fact_import(session, plan)
        print(f"Replaced {plan.scope_label} facts with {len(plan.rows)} CSV rows.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
