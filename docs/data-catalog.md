# Zeteo data catalogue

This is the field-level catalogue for the current SQLite POC serving model.
It documents SQLModel tables; source CSV headers can differ. `id` means a
SQLite integer primary key. `FK` means a declared database foreign key unless
the relationship explicitly says logical.

| Owner/source | Tables |
| --- | --- |
| ERP-owned imports, stored as Zeteo diagnostic read models | `company_hierarchy`, `company`, `gl_hierarchy`, `gl_account` |
| Zeteo-owned reference/configuration | `year`, `period`, `vdt_hierarchy`, `vdt_account`, `driver`, `driver_formula`, `driver_formula_term` |
| POC serving observations | `financial`, `driver_fact` |
| Zeteo-owned application setting | `app_settings` |

## Organization

### `company_hierarchy` — imported grouping nodes

| Field | Type/key | Meaning and use |
| --- | --- | --- |
| `code` | string, PK | Hierarchy-node identifier; used by parent and Company links. |
| `label` | string | Display name. |
| `parent_code` | string, nullable; self FK with `hierarchy_kind` | Parent node; null at hierarchy root. |
| `hierarchy_kind` | enum `BU`/`LEGAL` | Separates hierarchy variants; with `code`, has a unique constraint. |
| `order` | integer | Display/order within the hierarchy. |

### `company` — imported Company leaf and monetary scope

| Field | Type/key | Meaning and use |
| --- | --- | --- |
| `code` | string, PK | ERP Company code; scope for facts and monetary APIs. |
| `label` | string | Company display name. |
| `bu_node_code` | string, FK → `company_hierarchy.code` | Business Unit node containing the Company. |
| `order` | integer | Display/order within hierarchy. |
| `is_sampled` | boolean, default `false` | Company is included in POC sample facts. |
| `currency` | string | Declared local currency for money display/API envelope. |

## Calendar

### `year` — Zeteo fiscal years

| Field | Type/key | Meaning and use |
| --- | --- | --- |
| `year` | integer, PK | Fiscal/accounting year referenced by facts and Current Actual Period. |

### `period` — Zeteo fiscal-relative posting periods

| Field | Type/key | Meaning and use |
| --- | --- | --- |
| `period` | integer, PK | Fiscal period 1–12; never a stored `FYxx-Mxx` identifier. |
| `label` | string | Current display month label. |
| `quarter` | integer | Quarter 1–4 containing this period; supports display grouping. |

## Accounting

### `gl_hierarchy` — imported Reporting Root and Reporting Nodes

The row with null `parent_code` is the Reporting Root; all other rows are
Reporting Nodes. The served node type is derived, not stored.

| Field | Type/key | Meaning and use |
| --- | --- | --- |
| `code` | string, PK | Accounting hierarchy identifier. |
| `description` | string | Reporting-line label. |
| `parent_code` | string, nullable, FK → `gl_hierarchy.code` | Parent Reporting Node; null at root. |

### `gl_account` — imported Posting GL Account leaves

| Field | Type/key | Meaning and use |
| --- | --- | --- |
| `code` | string, PK | SAP/ERP Posting GL Account identifier. |
| `description` | string | Posting-account label. |
| `parent_code` | string, FK → `gl_hierarchy.code` | Reporting Node containing this leaf. |
| `normal_balance` | enum `D`/`C` | Debit/credit presentation rule for roll-up/display. |

### `financial` — financial fact

`id` is physical. The application logical fact key is `code × company × year
× period × source`.

| Field | Type/key | Meaning and use |
| --- | --- | --- |
| `id` | integer, PK | Surrogate SQLite row identifier. |
| `code` | string, indexed FK → `gl_account.code` | Posting GL Account observed. |
| `company` | string, indexed FK → `company.code` | Company observed. |
| `year` | integer, indexed FK → `year.year` | Fiscal year. |
| `period` | integer, indexed FK → `period.period` | Fiscal posting period. |
| `source` | enum `actual`/`budget`/`prior_year` | Scenario/data source. |
| `amount` | decimal `Numeric(24,2)` | Unscaled local-currency amount aggregated in reports. |

## Value Driver Tree

### `vdt_hierarchy` — Zeteo-owned non-leaf activity nodes

| Field | Type/key | Meaning and use |
| --- | --- | --- |
| `code` | string, PK | VDT Hierarchy Node identifier. |
| `description` | string | Activity label. |
| `parent_code` | string, application-resolved | Parent VDT or Accounting structure identifier. |
| `level` | integer | Display/tree depth. |

### `vdt_account` — Zeteo-owned terminal activity line

| Field | Type/key | Meaning and use |
| --- | --- | --- |
| `code` | string, PK | VDT Account identifier. |
| `description` | string | Activity-line label. |
| `parent_code` | string, FK → `vdt_hierarchy.code` | Containing VDT Hierarchy Node. |
| `fa_gl_code` | string, FK → `gl_account.code` | Accounting display/reconciliation anchor; not allocation or identity. |

## Drivers and formulas

### `driver` — reusable operational quantity

| Field | Type/key | Meaning and use |
| --- | --- | --- |
| `code` | string, PK | Reusable Driver identifier. |
| `description` | string | Driver label. |
| `unit` | enum | `currency-per-day`, `currency-per-month`, `percent`, `days`, `count`, or `ratio`. |
| `displayed_under` | string, nullable FK → `gl_account.code` | Optional display-only GL anchor for a terminal legacy Driver; not a calculation edge. |

### `driver_fact` — terminal Driver observation

`id` is physical. The application logical fact key is `code × company × year
× period × source`.

| Field | Type/key | Meaning and use |
| --- | --- | --- |
| `id` | integer, PK | Surrogate SQLite row identifier. |
| `code` | string, indexed FK → `driver.code` | Driver observed. |
| `company` | string, indexed FK → `company.code` | Company observed. |
| `year` | integer, indexed FK → `year.year` | Fiscal year. |
| `period` | integer, indexed FK → `period.period` | Fiscal posting period. |
| `source` | enum `actual`/`budget`/`prior_year` | Scenario/data source. |
| `amount` | decimal `Numeric(24,6)` | Raw Driver value; retained more precisely than money. |

### `driver_formula` — target calculation

| Field | Type/key | Meaning and use |
| --- | --- | --- |
| `code` | string, PK | Formula identifier. |
| `description` | string | Formula label. |
| `target_code` | string, logical polymorphic link | Target `driver`, `gl_account`, or `vdt_account`; deliberately not one physical FK. |
| `sign` | integer, default `1` | Adds or subtracts the formula result from the target. |

### `driver_formula_term` — ordered formula operands

| Field | Type/key | Meaning and use |
| --- | --- | --- |
| `id` | integer, PK | Surrogate row identifier. |
| `formula_code` | string, indexed FK → `driver_formula.code` | Formula containing the operand. |
| `term_index` | integer | Groups operands into one product/division term; terms are summed. |
| `operand_index` | integer | Order within the term. |
| `driver_code` | string, FK → `driver.code` | Driver operand. |
| `operator` | enum `×`/`÷`, default `×` | Operation after the first operand. |

## Shared application setting

### `app_settings` — intended singleton settings row

| Field | Type/key | Meaning and use |
| --- | --- | --- |
| `id` | integer, PK, default `1` | Singleton-row identifier. |
| `current_actual_year` | integer, nullable FK → `year.year` | Fiscal year of latest historical Actual. |
| `current_actual_period` | integer, nullable FK → `period.period` | Latest historical Actual period; used by Actual import and future simulation boundary. |

## Change rule

Update this catalogue with any persisted schema, field meaning, relationship,
ownership/source, or usage change. ADRs preserve historical trade-offs; they
do not replace the current table definition.
