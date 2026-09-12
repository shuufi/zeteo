# `general_ledger`/`GLNode` splits into `gl_hierarchy` (interior) + `gl_account` (leaves), matching the Company/BU precedent

`GLNode` (table `general_ledger`) has held every level of the Accounting hierarchy in one self-referencing table since ADR-0022: the single Reporting Root (`NPAT`), 98 Reporting Nodes, and 1083 Posting GL Account leaves, distinguished by a `node_type` enum and carrying a `level` int and a nullable `normal_balance`. ADR-0045 already made the equivalent split for Company (`company_hierarchy` decoupled from leaf-only `company`), and ADR-0046 explicitly declined to extend that split (or even a surface rename) to `GLNode` at the time, reasoning that it didn't yet reflect "a real leaf-vs-grouping split." This ADR revisits that call: GL's leaf depth is confirmed uneven (2 to 5 hops across branches, not a fixed number of tiers), the same structural signal that justified the Company split — GL was the one remaining master-data hierarchy still combining structure and leaves in a single table for no structural reason, only historical inertia.

## Decision

**Two tables, replacing `GLNode`/`general_ledger` entirely**:

- `gl_hierarchy` (class `GLHierarchy`): `code` (PK), `description`, `parent_code` (self-referencing FK -> `gl_hierarchy.code`, nullable — `NULL` only on `NPAT`, the sole root).
- `gl_account` (class `GLAccount`, leaf-only): `code` (PK), `description`, `parent_code` (FK -> `gl_hierarchy.code` — every posting account's parent is always an interior node), `normal_balance` (derived from the code's leading digit via the existing prefix rule, unchanged). Field stays named `description` (not `label`) — matches the existing `GLNode.description` convention this replaces; the CSV header and any future API surface can still say `label` without the underlying model needing to match, the same divergence ADR-0044 already established between `GLNode.description` and the `/api/gl` response's `label` field.

**No `hierarchy_kind`**: unlike `company_hierarchy`, GL has exactly one hierarchy shape today and no second variant planned. Add it later, additively, if one materializes — mirrors ADR-0045's own "add later if needed" reasoning, applied here to the axis that isn't needed yet instead of the one that was.

**No `level` column on either table**: real leaf depth is confirmed uneven — the identical justification ADR-0045 used to drop `level` from `company_hierarchy`. `seed_vdt.py`'s `level_of()`, which previously used a stored `gl_level_by_code` lookup as its base case, now computes GL depth by walking `parent_code` to the root at seed time instead.

**No `node_type` column on either table.** The distinction it encoded is fully derivable from table membership + structure: a `gl_account` row is always `"Posting GL Account"`; a `gl_hierarchy` row with `parent_code IS NULL` is `"Reporting Root"`; any other `gl_hierarchy` row is `"Reporting Node"`. The Root/Node distinction was never about reporting *capability* — `main.py` already lets a Comparison anchor at any Reporting Node, not just the Root — it's only "which single row is the top of the whole tree," which `parent_code IS NULL` already answers uniquely. `gl_tree.py`, `vdt_tree.py`, and `seed.py`'s call sites that branched on `NodeType.REPORTING_ROOT` directly switch to a `parent_code is None` check on `gl_hierarchy` rows. `nodeType` stays part of the `/api/gl` and `/api/financial/*` response contract (ADR-0044) — it's computed at tree-build/serve time now (`gl_tree._node_type()`), not stored.

**No stored `normal_balance` on `gl_hierarchy`.** Interior normal_balance (union of children's balances, `None` if mixed — e.g. Gross Profit) is computed at tree-build/serve time in `gl_tree.py` (`_normal_balance()`), the same rule as today, just not persisted. Matches `company_hierarchy` carrying no derived/rollup attributes at all.

**No `order` column.** Nothing today depends on stable sibling ordering for GL (unlike `company_hierarchy`'s `order`, added because the Business Picker needs stable display order); skip it rather than add unused structure.

**Downstream FK retargeting**:
- `Financial.code` → `gl_account.code`. Tightened: previously it could technically reference any `general_ledger` row, but `generate_gl_facts()` has only ever populated it from leaf nodes.
- `VdtAccount.fa_gl_code` (formerly `PostingActivityAccount.fa_gl_code`, see ADR-0047) → `gl_account.code`. Tightened for the same reason — confirmed empirically that all 17 distinct `FA GL` values in `backend/seeds/master/vdt_hierarchy_crew_cost.csv` are Posting GL Account leaves, zero exceptions. Adversarial review (Codex) flagged this as the one place worth a deliberate call rather than a silent tightening, since "non-reconciling anchor" reads more broadly than "posting account FK" — decided leaf-only is correct for the anchor's actual purpose.
- `VdtHierarchy.parent_code` (formerly `ActivityNode.parent_code`) stays an undeclared union-type FK (SQLite FK enforcement is off) — now spanning `vdt_hierarchy.code` or `gl_hierarchy.code` instead of `general_ledger.code`. The only real attach point in seed data (`PNL-0011`) is an interior node, never a leaf; this design doesn't change that shape, only which table the interior half of the union points at.
- `Driver.displayed_under` → `gl_account.code` (same tightening, same reasoning — always a leaf anchor).

**Seed-time integrity checks** (added per adversarial review, since the old single-table/enum shape used to make some of these invariants structurally impossible and the new split makes them merely conventional): exactly one `gl_hierarchy` row with `parent_code IS NULL`; no `gl_account` row with `parent_code IS NULL`; no hierarchy cycles; no orphaned rows in either table; no `gl_account.code` used as any row's `parent_code` (a leaf can never be a parent); no duplicate codes across the two seed CSVs.

**Seed data**: `backend/seeds/master/gl_hierarchy.csv` and `backend/seeds/master/gl_account.csv`, both headers `code,label,parent_code` — matching `bu_hierarchy_mapping.csv`'s convention and `vdt_hierarchy_crew_cost.csv`'s post-ADR-0047 relocation, rather than the older Title-Case, `docs/`-housed style. Generated by splitting the former `docs/anaplan_is_master_data.csv` on its `Node Type` column (`Posting GL Account` rows → `gl_account.csv`, everything else → `gl_hierarchy.csv`). `docs/anaplan_is_master_data.csv` is deleted afterward — no dual source of truth for the same rows, same reasoning ADR-0045 used to retire the BU-grouping columns previously embedded in `docs/misc_companies.csv`. No migration framework exists (`backend/seed.py` is a full rebuild-from-CSV script against a gitignored SQLite DB); this is a schema + seed-data change, not a live-data migration.

## Considered and rejected

**Keep `hierarchy_kind` for symmetry with `company_hierarchy`**: rejected — no second GL hierarchy variant exists or is planned; adding unused polymorphism now is pure speculation. Additive later if a real second variant appears.

**Keep `level` for cheaper reads / to match `VdtHierarchy`'s stored `level`**: rejected — real leaf depth is uneven, the same way ADR-0045 already rejected a fixed `level` for BU; deriving it once at seed time (for the one remaining consumer, `seed_vdt.py`) costs nothing at runtime.

**Keep `node_type` stored on both tables for symmetry / to avoid touching call sites**: rejected — every value is either constant (`gl_account` is always `Posting GL Account`) or derivable from one already-required column (`gl_hierarchy.parent_code`). Storing a value that's 100% redundant with structure just gives it a chance to drift.

**Leave `VdtAccount.fa_gl_code` as an undeclared union-type FK like `VdtHierarchy.parent_code`, in case a future VDT account anchors to an interior node**: rejected — no current data does this (verified: 0 of 17 distinct `FA GL` values reference anything but a leaf), and the anchor's documented purpose ("the real Posting GL Account it's conceptually explaining") is leaf-specific by definition. Revisit if that purpose changes.

**Keep `docs/anaplan_is_master_data.csv` around as a reference artifact**: rejected — `seed.py` would no longer read it once the two new CSVs exist, and an unread copy of the same data is exactly the duplicated-source-of-truth risk ADR-0045 already rejected once.

**Add an `order` column after all, once adversarial review found that `financial-client.ts`'s `buildDisplayRows()` renders `childIds` in raw order with no re-sort** (unlike `rankChildren()`, which sorts by variance): rejected for now — reading `gl_hierarchy`/`gl_account` as two separate queries always places a parent's interior children before its leaf children, which only differs from the original CSV's order for a parent with mixed child types (3 of 99 nodes today), and in all 3 of those, the leaf already came after the interior siblings in the source CSV — verified empirically, zero visible difference in today's real data. Documented as a known limitation in `gl_tree._load_gl_hierarchy()` rather than fixed, since fixing it properly would mean reopening the `order` rejection above for a gap with no current instance.

**Rename `GLFact`→`Financial` or `ActivityNode`/`PostingActivityAccount`→`VdtHierarchy`/`VdtAccount` as part of this ADR**: not applicable — both renames were already decided and applied by ADR-0046 and ADR-0047 respectively, ahead of this branch. This ADR only retargets the FKs those classes already had.

## Status

accepted
