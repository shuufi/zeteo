# Business Unit becomes a variable-depth `company_hierarchy` dimension, decoupled from `company` and ready for a future Legal hierarchy

`company_node` (ADR-0028) modelled exactly one grouping tier above Company — `MISC Group → Business Unit → Company` — as three `node_type` values (`Group`/`Business Unit`/`Company`) in one self-referencing table. A real second BU tier is now required: some Business Units (`MISCM`, `MMS`) sit under an intermediate `MISC Marine` node before reaching `MISC Group`, while others (`AET`, `ALAM`, `GAS`, `MHB`, `MISC`, `OBU`) parent directly to `MISC Group` — depth is genuinely uneven per BU, not a uniform extra layer. A separate Legal entity hierarchy, unrelated to the BU grouping, is also planned but not yet specified.

## Decision

**New table, decoupled from `company`**: `company_hierarchy` (`code`, `label`, `parent_code`, `hierarchy_kind`, `order`), self-referencing, arbitrary depth — no `level` column, since depth is confirmed uneven across BU branches and a future Legal hierarchy's shape is unknown. `hierarchy_kind` (`BU` today, `LEGAL` later) is one polymorphic table rather than a table per kind, matching the reasoning that already justified one `company_hierarchy` table over one-table-per-hierarchy-kind: one tree-walk implementation, one endpoint, one place to fix bugs, rather than duplicating both per kind added.

**Composite integrity constraint**: uniqueness and the self-referencing FK are both on `(code, hierarchy_kind)`, not `code` alone — `parent_code` + `hierarchy_kind` FK's into `(code, hierarchy_kind)`, so a `BU` node can never parent under a `LEGAL` node (or vice versa) even from a direct seed/SQL write, not just an app-level check.

**`company` becomes leaf-only**: `CompanyNode.node_type` and `CompanyNode.parent_code` are dropped entirely — every remaining `company` row is a real Company, nothing else ever occupies that table again. In their place, `CompanyNode` gets a new required (`NOT NULL`) FK `bu_node_code` → `company_hierarchy.code`, mirroring the existing `gl_fact.company` / `period_code` FK treatment: BU membership was never optional before (every company already had a mandatory `parent_code` into its BU), so the new FK stays mandatory too.

**One generic endpoint**: `GET /api/company-hierarchy?kind=BU` (and later `?kind=LEGAL`) rather than a per-kind route — same reasoning as the polymorphic table.

**Combined tree for the frontend**: the endpoint returns hierarchy nodes with Company leaves attached at the bottom via `bu_node_code`, one nested structure, each node carrying an explicit `isCompany` boolean. `BusinessPicker` walks one generic recursive tree, branching on `isCompany` instead of the old binary `companyType !== 'Company'` check, since depth is no longer fixed at 3 levels. `isCompany` is explicit rather than inferred from "has no children" — a grouping node with no companies assigned yet would otherwise be indistinguishable from a leaf.

**Seed data**: `backend/seeds/master/bu_hierarchy_mapping.csv`, adjacency-list shape (`code,label,parent_code,hierarchy_kind`), replacing the BU-grouping columns previously embedded in `docs/misc_companies.csv`. No migration framework exists (`backend/seed.py` is a full rebuild-from-CSV script, no Alembic) — this is a schema + seed-data change, not a live data migration.

## Considered and rejected

**Extend `company_node`'s `node_type` enum with a new tier (e.g. `Segment`) instead of a new table**: rejected — depth varies per BU branch, so a fixed extra `node_type` tier doesn't fit the real data, and a second hierarchy fork (Legal) landing in the same table later would turn `company` into a multi-hierarchy table with type-check spaghetti in every query.

**Keep `company_node`'s 3-level shape unchanged, add `company_hierarchy` as an additional parallel structure only some consumers use**: rejected — two sources of truth for "what BU does this company belong to" (old `parent_code` chain and new `company_hierarchy` chain) that must stay in sync is exactly the ambiguity a dimension model exists to prevent.

**Separate table per hierarchy kind (`bu_hierarchy_node`, later `legal_hierarchy_node`)**: rejected in favor of one polymorphic `company_hierarchy` table — the column set is identical across kinds, and a per-kind table doubles the tree-walk/endpoint code for every hierarchy added.

**Fixed `level` int column** (as `GLNode` has): rejected — actual BU data confirms uneven depth per branch, and Legal's eventual depth is unknown; a `level` column can be added later as an additive migration once a real need for fast level-filtering appears.

**Nullable `bu_node_code`**: rejected — BU membership was mandatory before this change (every `company` row already had a required `parent_code`), so making the replacement FK optional would introduce a data state ("company with no BU") nothing downstream is designed to handle.

## Status

accepted
