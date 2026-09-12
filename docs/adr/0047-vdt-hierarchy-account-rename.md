# `ActivityNode`/`PostingActivityAccount` renamed to `VdtHierarchy`/`VdtAccount`

`ActivityNode`/`PostingActivityAccount` (ADR-0033) were named for the domain concept they modelled at the time — an activity-based costing tree grafted onto GL. But "Activity" never became the product's own vocabulary: every screen, route, and glossary entry (CONTEXT.md, the URS Terminology table) calls this "VDT" (Value Driver Tree). "Activity Node"/"Posting Activity Account" read as unrelated jargon next to VDT Explorer, VDT Variance Analysis, VDT Reconciliation, VDT Sensitivity Analysis — a new reader has no textual signal these classes are VDT's own tables.

ADR-0046 separately rejected applying the `<entity>`/`<entity>_hierarchy` leaf/grouping split naming pattern to `ActivityNode`/`PostingActivityAccount`, on structural grounds: VDT isn't a second hierarchy parallel to GL the way Legal will be parallel to BU, it grafts onto GL's own tree and reuses shared `GLNode` rows outside the pilot scope. **That structural reasoning is unaffected by this ADR** — this is a vocabulary-only rename, not a reopening of ADR-0046's carve-out. The two tables stay exactly as structured; only their names change to say what they are.

## Decision

**Rename the classes, tables, and every consumer**:
- `ActivityNode` (table `activity_node`) → `VdtHierarchy` (table `vdt_hierarchy`)
- `PostingActivityAccount` (table `posting_activity_account`) → `VdtAccount` (table `vdt_account`), `parent_code` FK retargeted to `vdt_hierarchy.code`

`VdtAccount` over `VdtLedger` for the leaf: it's a postable target reconciling to a real GL account via `fa_gl_code`, the same role a GL account plays — "account" is the standard accounting noun for that, and it pairs with `VdtHierarchy` under the same `<entity>`/`<entity>_hierarchy` naming shape ADR-0046 formalized (used here purely as a naming convention, not a claim that this is the leaf/hierarchy structural split ADR-0046 was actually deciding). "Ledger" was rejected — `general_ledger` already means something else in this codebase (the GL book itself), and reusing it for a VDT leaf row would recreate the exact naming collision this ADR exists to remove.

**API-facing type strings renamed to match**: `"Activity Node"` → `"VDT Hierarchy Node"`, `"Posting Activity Account"` → `"VDT Account"` — in the `nodeType` values `vdt_tree.py` emits, the frontend's `GlNodeType` union, `variance_analysis.py`'s materiality-selection constant, and the CSV `Node Type` column. Leaving the class renamed but the wire-format string untouched (`VdtHierarchy` emitting `nodeType: "Activity Node"`) would recreate the exact mismatch this ADR exists to fix.

**Type string is `"VDT Hierarchy Node"`, not bare `"VDT Hierarchy"`**: the class is `VdtHierarchy` (Pascal-cased, not full-cap-acronym — matches the existing `GlNodeType` precedent of `Gl` not `GL`), but the display/type string needed a `Node` suffix. Bare `"VDT Hierarchy"` collides with the pre-existing glossary term "VDT hierarchy" (the whole tree — see CONTEXT.md) — same words, distinguished only by capitalization. Every other node-type string in this system already ends in a noun describing the node's role (`Reporting Root`, `Reporting Node`, `Posting GL Account`) rather than repeating the tree's own name, so `"VDT Hierarchy Node"` matches that pattern and reads unambiguously distinct from "the VDT hierarchy" (the tree).

**Seed data relocated alongside the rename**: `docs/vdt-hierarchy-crew-cost.csv` → `backend/seeds/master/vdt_hierarchy_crew_cost.csv` (snake_case, matching the sibling `bu_hierarchy_mapping.csv` precedent from ADR-0045), `Node Type` column values updated to match. No Alembic/migration framework exists — `backend/seed.py` is a full rebuild-from-CSV script, so this is a schema + seed-data change, not a live data migration.

**Not moved in this ADR**: `docs/anaplan_is_master_data.csv` and `docs/misc_companies.csv` stay in `docs/` — a broader `seeds/master/` consolidation is a separate, unrelated change.

## Status

accepted
