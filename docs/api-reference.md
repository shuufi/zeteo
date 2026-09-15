# Zeteo API reference

The backend runs at `http://localhost:8000`. FastAPI exposes the live,
machine-readable contract at `/openapi.json` and the interactive contract at
`/docs`. This guide explains the current business-facing semantics; it does
not repeat every response property from the generated schema.

All dates use integer `year` plus fiscal-relative integer `period` (1–12).
There are no `FYxx-Mxx` request codes. `month` in API parameters means the
same fiscal period number.

## Common contracts

Monetary routes resolve `scope` to exactly one Company. Successful monetary
responses include `scopeKind: "company"`, `currency`, `partial: false`,
`sampledCompanyCount: 1`, and `totalCompanyCount: 1`. A non-Company scope is
rejected with 422 rather than combining currencies; an unknown scope is 404.

| Selection | Parameters |
| --- | --- |
| Fiscal year | `year` |
| Quarter | `year` + `quarter` (1–4) |
| Fiscal month | `year` + `month` (1–12) |

`quarter` and `month` are mutually exclusive. Comparison endpoints require
both selections to have the same grain. `ytd=true` means fiscal-year start
through the selected month or quarter.

## Reference data

| Method and path | Parameters | Returns |
| --- | --- | --- |
| `GET /api/companies` | none | Company leaves, including currency and POC sampling marker. |
| `GET /api/company-hierarchy` | `kind` optional; default `BU` | Company grouping tree for `BU` or `LEGAL`. |
| `GET /api/periods` | none | Year → Quarter → Period picker tree built from integer calendar reference data. |
| `GET /api/gl` | none | Accounting hierarchy/master data only; no financial amounts. |

## Financial

| Method and path | Required parameters | Purpose |
| --- | --- | --- |
| `GET /api/financial/tree` | `scope`; period selection | Accounting statement tree for one Company and selected period. |
| `GET /api/financial/comparison` | `scope`, `node`, `yearA`, `yearB`; optional same-grain `quarterA`/`quarterB` or `monthA`/`monthB` | Changed Accounting subtree between two periods. `node` must be a Reporting Root or Reporting Node. |

The tree response contains `nodes` keyed by Accounting code. A scope with no
modelled data returns `notYetModelled: true` and an empty node map. A missing
seeded Accounting model is a server error.

## Value Driver Tree

| Method and path | Required parameters | Purpose |
| --- | --- | --- |
| `GET /api/vdt/tree` | `scope` and either a normal period selection or `trailingEndYear` + `trailingEndPeriod` | VDT tree. Trailing mode returns resolved `months` and takes precedence if both modes are supplied. |
| `GET /api/vdt/comparison` | `scope`, `node`, `yearA`, `yearB`; optional same-grain quarter/month pairs; `ytd` optional | VDT subtree comparison. `node` must be Reporting Root, Reporting Node, or VDT Hierarchy Node. |
| `POST /api/vdt/variance-analysis` | Same query parameters as VDT comparison | Evidence-bound narrative for selected VDT comparison; returns `varianceAnalysis`. |
| `POST /api/vdt/trend-analysis` | `scope`, and exactly one of `year` or `trailingEndYear` + `trailingEndPeriod`; optional `source=actual|budget` | Whole-window trend narrative for fixed pilot VDT anchor; returns `trendAnalysis`. |
| `GET /api/vdt/reconciliation` | `scope`, `node`, normal period selection; `ytd` optional | VDT subtree plus only the linked Accounting GL nodes required for VDT Account `FA GL` anchors. |

Trailing mode walks backward from its selected month for up to twelve periods.
It deliberately returns a partial window when the POC has no earlier seeded
year. Reconciliation does not score or colour the VDT–Accounting difference:
the independent VDT estimate is not required to reconcile to Accounting.

## Sensitivity

`POST /api/vdt/sensitivity` accepts JSON and returns Server-Sent Events
(`text/event-stream`). Validation happens before streaming. The stream emits
`progress` events and exactly one `result` event; an unexpected calculation
failure is emitted as an `error` event.

| JSON field | Required | Meaning |
| --- | --- | --- |
| `scope` | yes | Company code. |
| `scopeNode` | yes | VDT node constraining candidate terminal Drivers. |
| `bumpPct` | yes | Sensitivity bump from 1 to 20 inclusive. |
| `source` | no | `actual` (default) or `budget`. |
| `year` | one mode | Fiscal-year window. |
| `trailingEndYear` | other mode | Trailing-window anchor year. |
| `trailingEndPeriod` | with trailing year | Trailing-window anchor period, 1–12. |

Exactly one window mode is valid: `year`, or both trailing fields. Sensitivity
uses in-memory Driver overrides and never persists a scenario.

## Error conventions

| Status | Meaning |
| --- | --- |
| 400 | Invalid combination, unsupported source, or incompatible comparison grain. |
| 404 | Unknown scope, node, fiscal year/period, or no VDT model for selected Company. |
| 422 | Validation failure, including non-Company monetary scope or invalid sensitivity bump. |
| 500 | Required seeded model is unavailable. |
| 503 | Configured LLM narrative provider was unavailable. |

Keep this guide aligned with `backend/api/routes.py`; use `/docs` to inspect
the exact OpenAPI schema after changing a route.
