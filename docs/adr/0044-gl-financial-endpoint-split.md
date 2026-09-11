# Split `/api/gl` (financial figures) into `/api/financial`, freeing `/api/gl` for chart-of-accounts master data

`GET /api/gl/tree` and `GET /api/gl/comparison` never served GL master data — they served computed Actual/Budget/Prior-Year figures rolled up over the GL/FSI account hierarchy (ADR-0022), scoped to a company and period. The `/api/gl` path named the *hierarchy the figures are computed over*, not what the endpoint actually returns, which is financial figures. This mismatch carried through the frontend as `gl-client.ts`/`gl-store.svelte.ts`/`glStore` — none of which are chart-of-accounts concerns either. Meanwhile there was no endpoint at all for the GL hierarchy's own master data (code/description/parent/node type/normal balance), the way `GET /api/companies` and `GET /api/periods` already serve their respective master data.

## Decision

**Rename**: `GET /api/gl/tree` → `GET /api/financial/tree`, `GET /api/gl/comparison` → `GET /api/financial/comparison`. Same params, same response shape, same behavior — naming only. Backend handlers renamed `get_gl_tree`/`get_gl_comparison` → `get_financial_tree`/`get_financial_comparison`. Frontend `gl-client.ts`/`gl-store.svelte.ts` → `financial-client.ts`/`financial-store.svelte.ts`, `glStore` → `financialStore`, `GlScopeMeta` → `FinancialScopeMeta`.

**New endpoint**: `GET /api/gl` — the GL/FSI chart-of-accounts hierarchy itself, no financial figures. No params: `general_ledger` has no company column, so there is nothing to scope by — it's global master data, mirroring `GET /api/companies`/`GET /api/periods` exactly (both also take no params). No "not seeded" guard either, for the same reason those two don't have one: an empty hierarchy returning `{}` is an honest answer, not a misleading one (unlike an empty `gl_fact` table silently producing all-zero figures, which is why the financial routes *do* guard).

**Response shape**: `{id, label, parentId, childIds, nodeType, normalBalance}` per node — `label` (not `name`) to match `/api/companies`/`/api/periods`'s master-data convention rather than `/api/financial/*`'s figure-bearing `name` field. `normalBalance` included (nullable — only meaningful on `Posting GL Account` leaves) since it's already on the row and cheap; `level` (raw depth int) excluded since nothing consumes it and it's redundant with a `childIds`/`parentId` walk.

**Backend module**: no new file. `gl_tree.py` already owns the GL domain's rows (`GLNode`) regardless of which route consumes them — matches `company_tree.py` (owns `resolve_scope` alongside `build_company_tree`) and `periods.py` (owns month/window helpers alongside `build_period_tree`), both "one file per domain entity," not "one file per concern." Added `build_gl_master_tree()`, and factored the `node_by_code`/`children_by_parent` construction `build_tree()` already did into a shared `_load_gl_hierarchy()` helper both functions call, rather than duplicating the walk.

**Frontend**: backend-only for now — no `gl-client.ts`/`gl-store.svelte.ts` equivalent for the new master-data endpoint. No current screen needs raw chart-of-accounts data on its own; every existing consumer wants figures (hence `financial-store`). Add a client/store when a real screen needs it.

**Historical ADRs**: edited in place. ADR-0022, ADR-0025, ADR-0027, ADR-0031, ADR-0033, ADR-0034 each mention `GET /api/gl/tree` or `GET /api/gl/comparison` as then-current fact; updated to `GET /api/financial/tree`/`GET /api/financial/comparison` so they no longer describe a route that doesn't exist. (Normal ADR practice would leave historical text as-is and let a new ADR supersede it; this project's owner explicitly chose to edit the history here instead, given the endpoints' behavior is completely unchanged — only the name was ever wrong.)

## Considered and rejected

**Leave `/api/gl/tree`/`/api/gl/comparison` as-is, just add `/api/gl-master` or similar for the new endpoint**: rejected — it would permanently enshrine the wrong name on the two heavily-used routes while relegating the correctly-named one to an awkward suffix. The mismatch was the actual problem being fixed.

**Fold master-data fields into `/api/financial/tree`'s existing response** (e.g. an optional `?figuresOnly=false` flag): rejected — conflates two different callers' needs (a master-data browser needs no scope/period at all; a financial-figures screen always needs both) into one endpoint with conditional shape, instead of two endpoints that each do one thing.

**New dedicated module for the master-data builder**: rejected in favor of keeping it in `gl_tree.py` — see `company_tree.py`/`periods.py` precedent above.

## Status

accepted
