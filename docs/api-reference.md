# API Reference

Hand-maintained reference for the FastAPI backend (`backend/main.py`). No
`response_model`s are declared on the routes, so the auto-generated
`/openapi.json` / Swagger UI (`/docs`) is untyped — this file is the source of
truth for shapes. Keep it in sync when routes change.

Base URL (dev): `http://localhost:8000`. All routes are prefixed `/api`.

## Conventions

**Scope.** Every financial route takes `scope`, a Company code (e.g.
`MSC-01`). Group/Business-Unit rollups are rejected — cross-company rollups
need FX conversion, which isn't implemented (see docs/adr/0028,
docs/adr/0035). Every response that resolves a scope carries this envelope:

| field | type | meaning |
|---|---|---|
| `scope` | string | echoes the request |
| `scopeKind` | `"company"` | always `"company"` today |
| `currency` | string | the company's currency |
| `partial` | bool | always `false` today |
| `sampledCompanyCount` / `totalCompanyCount` | int | `1`/`1` today |
| `notYetModelled` | bool | `true` if the company has no seeded VDT/GL data — callers should render an empty/placeholder state, not an error |

**Node maps.** Tree endpoints return `nodes` as a flat `dict[code -> node]`,
not a nested structure — each node carries `parentId` and `childIds` and the
client walks it. A GL/VDT node looks like:

```json
{
  "id": "V201000000",
  "name": "SOC Crew Cost",
  "parentId": "V200000000",
  "childIds": ["V201100000", "V201200000"],
  "nodeType": "Activity Node",
  "unit": "money",
  "actual": 1234567.89,
  "budget": 1200000.0,
  "priorYear": 1100000.0,
  "monthlyActual": [...12 or window-length floats...],
  "monthlyBudget": [...],
  "monthlyPriorYear": [...],
  "direction": "favourable"
}
```

`direction` is `"favourable" | "adverse" | "neutral"` (sign convention already
applied — see `normal_balance` handling in `gl_tree.py`). Money values are
plain rounded floats (2dp), not strings — see `_money_json`.

**Errors.** No custom error envelope — plain FastAPI `HTTPException`, body is
`{"detail": "<message>"}`. Common codes used across routes:

| code | meaning |
|---|---|
| 400 | malformed/inconsistent params (e.g. mismatched period grain, missing mode selector) |
| 404 | unknown scope/period/node code |
| 422 | semantically invalid input (e.g. company-level scope required, bump% out of range) |
| 500 | data not seeded, or a resolved company is missing required data |
| 503 | an LLM-backed narrative call failed upstream |

**Periods.** A period `code` can be a Year, Quarter, or Month (see
`docs/adr/0025`). Two window-selection modes recur across VDT routes:
*Financial Year mode* (`period`/`year`, any grain) and *Trailing mode*
(`trailingEnd`, a Month code anchoring a trailing N-month window — see
`docs/adr/0042`). Where both exist on a route they're mutually exclusive.

---

## Master data

### `GET /api/companies`
Company master data — leaves only, no hierarchy (see `docs/adr/0045`). No params.

Returns a node map: `{code: {id, label, currency, isSampled, buNodeCode}}`. `buNodeCode`
is the required FK into `company_hierarchy` (see below) — walk that endpoint to
resolve a company's BU chain up to MISC Group.

### `GET /api/company-hierarchy?kind=BU`
Company grouping hierarchy above Company (MISC Group and its descendants) with
Company leaves attached via `buNodeCode`, one combined tree — see
`docs/adr/0045-company-hierarchy-bu-legal-dimension.md`. Depth is variable, not
fixed at one BU tier: some branches (e.g. `MISC Marine`) sit between a Business
Unit and MISC Group, others parent directly to MISC Group. `kind` selects the
hierarchy (`BU` today; `LEGAL` planned, not yet seeded).

Returns a node map: `{code: {id, label, parentId, childIds, kind, isCompany}}`,
with Company leaves merged in as childless nodes under their `buNodeCode`
parent. `isCompany` distinguishes a real Company leaf from a grouping node
explicitly — a grouping node with no companies yet would otherwise be
indistinguishable from a leaf by childIds alone.

### `GET /api/periods`
Fiscal Year/Quarter/Month hierarchy. No params.

Returns a node map: `{code: {id, label, periodType, parentId, childIds, order}}`.

### `GET /api/gl`
GL/FSI chart-of-accounts hierarchy — master data only, no financial figures
(see docs/adr/0044). No params: the chart of accounts is global, not
per-company. No "not seeded" guard either — an empty hierarchy returning `{}`
is an honest answer, not a misleading one.

Returns a node map: `{code: {id, label, parentId, childIds, nodeType, normalBalance}}`.
`nodeType` is `"Reporting Root" | "Reporting Node" | "Posting GL Account"`;
`normalBalance` is `"D" | "C" | null` (only set on `Posting GL Account` leaves).

---

## Financial (computed figures over the GL hierarchy)

### `GET /api/financial/tree`
FSI/GL account hierarchy with Actual/Budget/Prior-Year, for one scope and
period. (Renamed from `/api/gl/tree` — see docs/adr/0044; the GL hierarchy's
own master data now lives at plain `GET /api/gl`.)

| param | required | notes |
|---|---|---|
| `scope` | yes | Company code |
| `period` | no | Year/Quarter/Month code; omitted = latest fiscal year in full |

Response: scope envelope + `{notYetModelled, period, nodes}`.

Errors: 500 if unseeded, 404 unknown scope, 422 non-company scope, 404 unknown period.

### `GET /api/financial/comparison`
Same-grain diff of a GL subtree between two periods. (Renamed from
`/api/gl/comparison` — see docs/adr/0044.)

| param | required | notes |
|---|---|---|
| `scope` | yes | |
| `node` | yes | must resolve to `Reporting Root` or `Reporting Node` |
| `periodA` / `periodB` | yes | must be the same `periodType` |

Response: scope envelope + `{node, periodA, periodB, nodes}` — `nodes` is the
diffed subtree (each entry gains delta fields from `diff_subtree`).

Errors: 400 grain mismatch, 404 unknown node, 400 wrong node type.

---

## VDT (Value Driver Tree)

### `GET /api/vdt/tree`
VDT hierarchy (Reporting Root → Activity Node → Posting Activity Account),
Financial Year or Trailing mode.

| param | required | notes |
|---|---|---|
| `scope` | yes | |
| `period` | no | Financial Year mode (Year/Quarter/Month code) |
| `trailingEnd` | no | Trailing mode anchor (Month code); wins if both given |

Response: scope envelope + `{notYetModelled, period, months?, nodes}` —
`months` (the resolved window's month codes) is only present in Trailing mode.
Node map entries add `faGlCode` on `Posting Activity Account` leaves (their FA
GL anchor — see docs/adr/0033).

Errors: 500 unseeded, 404/422 scope, 404 unknown period, 404 unknown
`trailingEnd`, 400 `trailingEnd` not a Month.

### `GET /api/vdt/comparison`
Same-grain VDT diff between two periods, optional YTD accumulation.

| param | required | notes |
|---|---|---|
| `scope`, `node`, `periodA`, `periodB` | yes | `node` must be `Reporting Root`/`Reporting Node`/`Activity Node` |
| `ytd` | no, default `false` | accumulate from year start instead of a single period |

Response: scope envelope + `{node, periodA, periodB, ytd, nodes}` (diffed subtree).

### `POST /api/vdt/variance-analysis`
LLM narrative over the same comparison `/api/vdt/comparison` computes (shared
via `_vdt_comparison_payload`, docs/adr/0034). Same query params as
`/api/vdt/comparison`. Cached per `(scope, node, periodA, periodB, ytd)`.

Response: `{"varianceAnalysis": {headline, netAmount, bullets}}`. Each bullet:
`{nodeId, nodeName, text, amount, deltaPct, contributionPct}`.

Errors: 404 if scope not yet modelled, 503 if the LLM call fails
(`VarianceAnalysisUnavailable`).

### `POST /api/vdt/trend-analysis`
Whole-window MoM trend narrative, always anchored at the fixed pilot node
(`V201000000`, SOC Crew Cost — see docs/adr/0040). Body is query params, not
JSON.

| param | required | notes |
|---|---|---|
| `scope` | yes | |
| `year` | one of `year`/`trailingEnd` | Financial Year mode |
| `trailingEnd` | one of `year`/`trailingEnd` | Trailing mode |
| `source` | no, default `actual` | `"actual"` \| `"budget"` |

Response: `{"trendAnalysis": {headline, source, bullets}}`. Each bullet:
`{nodeId, nodeName, nodeType, text, series, rootSeries, flaggedMonths, peakMonthIndex}`.
Cached per resolved `(scope, window_months, source)` — a Financial Year and a
Trailing request resolving to the same months share a cache entry
(docs/adr/0042).

Errors: 400 both/neither of `year`/`trailingEnd`, 400 bad `source`, 404
scope/period, 503 LLM failure.

### `GET /api/vdt/reconciliation`
VDT subtree at `node` plus the Accounting (GL) anchor nodes its Posting
Activity Account leaves point to (docs/adr/0033, docs/adr/0037) — the two
hierarchies are independent estimates, not required to reconcile.

| param | required | notes |
|---|---|---|
| `scope`, `node` | yes | `node` must be `Reporting Root`/`Reporting Node`/`Activity Node` |
| `period` | no | Financial Year mode only (no Trailing mode on this route) |
| `ytd` | no, default `false` | |

Response: scope envelope + `{node, period, ytd, accounting: {nodes}, vdt: {nodes}}`.
No delta/polarity coloring between the two — the gap is informational.

---

## VDT Sensitivity Analysis (streaming)

### `POST /api/vdt/sensitivity`
Elasticity/tornado-chart analysis: bumps each terminal driver ±`bumpPct` and
reruns NPAT, one driver-direction at a time (docs/adr/0043). First (and only)
streaming endpoint in the backend — validation happens as ordinary HTTP
errors *before* the SSE stream opens, so a client never has to parse an error
out of an event frame.

Request body (JSON):

```json
{
  "scope": "MSC-01",
  "scopeNode": "V201000000",
  "bumpPct": 5.0,
  "source": "actual",
  "year": "FY24",
  "trailingEnd": null
}
```

Exactly one of `year` / `trailingEnd` must be set. `bumpPct` must be in
`[1, 20]`. `source` is `"actual"` \| `"budget"`.

Response: `Content-Type: text/event-stream`, each frame `data: <json>\n\n`.
Event types, in order:

- `{"type": "progress", "completed": N, "total": M}` — one per per-driver-direction rerun.
- `{"type": "candidate", "candidate": {...}}` — emitted once a candidate's own result is final (both directions, or immediately for a skip-compute N/A). Lets the frontend render the tornado chart progressively.
- exactly one `{"type": "result", ...}` at the end, carrying the authoritative ranking (rank order isn't stable until every candidate is in).
- `{"type": "error", "detail": "..."}` if computation raises mid-stream.

`candidate` shape: `{driverCode, description, unit, up, down, rankMagnitude, na, naReason}`
where `up`/`down` are `{elasticityPct, npatImpact, polarity}` and `naReason` is
one of `"baseline-driver-zero" | "divide-by-zero" | "baseline-npat-zero"`.

`result` event adds: `{source, months, baselineNpat, npatNearZero, reason,
candidateCount, ranked, candidates, scope, scopeNode, scopeName, currency,
bumpPct, monthLabels, windowLabel}` — `ranked` is the top 10 non-N/A candidates
by `|rankMagnitude|`; `candidates` is every candidate. `reason` (top-level
N/A explanation) is `"no-terminal-drivers" | "all-na" | null`.

Errors (before streaming starts): 422 `bumpPct` out of range, 400 bad
`source`, 400 both/neither of `year`/`trailingEnd`, 500 unseeded, 404/404
scope/period, 422 run exceeds `SENSITIVITY_MAX_CYCLES` (cost cap), 404
unknown `scopeNode`.

If the client disconnects mid-stream, the server stops consuming the
generator (checked via `request.is_disconnected()` after each event) — no
further compute happens for an abandoned run.
