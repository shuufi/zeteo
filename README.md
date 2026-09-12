# Zeteo

Zeteo is a financial-performance diagnostic POC. It combines Accounting,
Value Driver Tree (VDT), and Driver data to explain financial movement.

## Run locally

Install the backend dependencies, seed the local SQLite database, then start
the development servers:

```bash
pip install -r backend/requirements.txt
python -m backend.scripts.seed
./start-servers.sh
```

The backend runs at `http://localhost:8000`; the frontend runs at
`http://localhost:5173`.

## POC budget import

The POC uses a validated script rather than an admin page or a physical
Bronze/Silver/Gold pipeline. It writes the selected budget data directly to
the SQLite serving model. See [ADR-0049](docs/adr/0049-poc-budget-import-script.md)
for the boundary and rationale.

Choose one four-digit calendar Year and one dataset type for each import. The
script maps the selected source Year and `period` (1–12) to Zeteo's internal
Fiscal Year/Month codes. Files must not contain a source column.

Financial Budget CSV:

```csv
company_code,year,period,gl_account_code,amount
0190,2026,1,5100100100,125000.00
```

Driver Budget CSV:

```csv
company_code,year,period,driver_code,value
0190,2026,1,DRV-CREW-COMPLEMENT,24
```

Validate first; this is also the default when `--apply` is omitted:

```bash
python -m backend.scripts.import_budget \
  --year 2026 --type financial --file ./fy26-financial-budget.csv --dry-run
```

After a successful dry run, apply the replacement:

```bash
python -m backend.scripts.import_budget \
  --year 2026 --type financial --file ./fy26-financial-budget.csv --apply
```

The script displays the number of existing Budget rows in the chosen Fiscal
Year and dataset type, then asks for confirmation. On confirmation it replaces
that entire scope in one SQLite transaction. Actual facts and every other
Fiscal Year/type remain unchanged.

The import rejects the whole CSV when its headers are wrong, a month/value is
invalid, a Company/GL Account/Driver code is absent from Zeteo master data, or
the file repeats a Company × code × month key. Dummy POC data does not need to
cover every Company, account, Driver, or month.

## POC admin menu

Run one interactive entry point for routine POC administration:

```bash
python3 backend/scripts/admin.py
```

From the repository root, the equivalent module command also works:

```bash
python3 -m backend.scripts.admin
```

The menu can set the global **Current Actual Period**, import Budget, import
Actual, and show the current data status. It is stored in the shared
`app_settings` row, not in Simulation-specific configuration. Current Actual Period is a
Month-only setting such as calendar year `2026`, period `6` (internally
`FY26-M06`). It marks the latest historical Actual month; the forthcoming
Simulation feature will preserve Actuals up to that month and use Budget as
its baseline after it.

Actual files use the same headers as Budget files. The menu selects a Company
and filters the CSV to rows matching both that Company and Current Actual
Period; it reports skipped rows and rejects a file with no matching rows. On
confirmation, it replaces Actual facts only for that Company × Month × type.
See [ADR-0050](docs/adr/0050-poc-admin-current-actual-period.md).

## Validation

```bash
pytest -q
```
