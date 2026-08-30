# Period becomes hierarchical master data — Year → Quarter → Month, postable at Month only

`gl_fact` has no year at all today — just a bare `month: int` (1-12), leaving a single implicit fiscal year (ADR-0023's fact-table description already calls this column "period" in prose, but the actual column is `month`, an untyped int with no calendar structure). Period becomes a real dimension table, `period` (`code`, `parent_code`, `period_type`), self-referencing the same adjacency-list + type-discriminator shape as `gl_node`: a Year row (`FY26`) parents four Quarter rows (`FY26-Q1`..`Q4`, calendar-aligned, Jan start), each parenting three Month rows (`FY26-M01`..`M12`). Only one fiscal year is seeded for now — the schema doesn't prevent more, it just isn't asked to carry them yet.

"Postable" — able to carry `gl_fact` rows — is not a stored flag; it's `period_type == Month`, enforced by making `gl_fact.period_code` a foreign key into `period.code` and only ever seeding Month-grain codes there (replacing the bare `month` int). Year and Quarter rows exist purely for rollup/reporting grouping, the same relationship Reporting Nodes have to Posting GL Accounts in `gl_node`.

This also fixes a latent gap `gl_tree.py`'s `compute()` had: `gl_fact` already stores real monthly rows for all three scenarios (actual/budget/prior_year), but the tree-walk only builds a `monthlyActual` array — budget and prior_year are collapsed straight to annual totals, and the one place that needed a single month (`getMonthlyNodeView` in `gl-client.ts`) prorated them from that annual figure instead of reading the real row. With Month now the formal postable grain, budget and prior_year get proper monthly rollup too; the proration hack is removed.

`GET /api/gl/tree` gains an optional `period_code` param (Year/Quarter/Month code) that scopes the rollup to just that period's months server-side; omitted, it behaves exactly as today (full-year totals). A new `GET /api/periods` returns the Year→Quarter→Month tree so the frontend can build a picker without hand-rolling calendar math.

Rejected: separate `year`/`quarter`/`month` tables with explicit FKs — more type-safe, but diverges from the `gl_node` precedent for no real benefit here, and would need its own bespoke join/rollup logic instead of reusing the adjacency-list walk already proven for the GL hierarchy.

**Status**: accepted
