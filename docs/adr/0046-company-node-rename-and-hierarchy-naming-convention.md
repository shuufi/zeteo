# `CompanyNode`/`GLFact` renamed to `Company`/`Financial`; `<entity>`/`<entity>_hierarchy` naming formalized for future dimensions

ADR-0045 split `company` into a leaf-only table plus a separate `company_hierarchy` grouping table, but left the SQLModel class named `CompanyNode` — a leftover from the pre-split shape, where it really was a tree node carrying `node_type`/`parent_code`. Post-split it's a plain master-data leaf (table already named `company`), so the class name no longer matched what it modelled, or the table it backed.

Separately, ADR-0044 renamed the `/api/gl/*` routes to `/api/financial/*` and the fact table's `__tablename__` to `financial` (it was never GL master data, always computed/raw financial figures) — but left the SQLModel class named `GLFact`, the same class/table mismatch as `CompanyNode`.

## Decision

**Rename the classes only**: `CompanyNode` → `Company` (in `models.py` and every consumer: `company_tree.py`, `seed.py`, `backend/tests/conftest.py`), and `GLFact` → `Financial` (in `models.py`, `gl_tree.py`, `driver_engine.py`, `seed.py`, and every test that references it). No table/column change in either case — `__tablename__` was already `company` and `financial` respectively. Matches the table name and the domain term ("Company", CONTEXT.md/URS Terminology; "Financial" is already the route/screen name per ADR-0044).

**Formalize the naming pattern going forward**: when a domain is genuinely split into a leaf/master table and a separate self-referencing grouping table — per ADR-0045's reasoning (variable depth, and/or a second hierarchy_kind sharing the same column shape) — name them `<entity>` (class `<Entity>`) and `<entity>_hierarchy` (class `<Entity>Hierarchy`), mirroring `company`/`company_hierarchy` exactly.

**Explicitly not applied to `GLNode`/`general_ledger`, `ActivityNode`/`activity_node`, or `Period`/`period`**: none of these are an actual leaf-plus-grouping split.
- `GLNode` is one hierarchy with no second `hierarchy_kind` sharing its shape and no evidence of one planned — splitting it now would be speculative generality with nothing to amortize the cost across.
- `ActivityNode`/`PostingActivityAccount` (VDT) already are two tables, but VDT isn't a second hierarchy parallel to GL the way Legal will be parallel to BU — it grafts onto GL's own tree at specific attachment points and literally reuses shared `GLNode` rows outside the pilot scope (see `vdt_tree.py`). A polymorphic `hierarchy_kind` merge would force duplicating those shared rows across two kinds — the exact "two sources of truth" duplication ADR-0045 already rejected.
- `Period` is one combined Year/Quarter/Month tree with no second period-adjacent hierarchy kind.

## Considered and rejected

**Rename `GLNode`/`ActivityNode`/`Period` anyway, purely for surface naming consistency with `Company`/`CompanyHierarchy`**: rejected — none of them reflect a real leaf-vs-grouping split, so renaming would invite a phantom `general_ledger_hierarchy` or `activity_node_hierarchy` table with no reason to exist, and would rename away `ActivityNode`, an established domain term (CONTEXT.md), for no structural gain.

## Status

accepted
