# Financial Comparison is a new page with a server-computed, node-scoped diff endpoint

`/financial` becomes a hover dropdown ("Financial" nav item, unchanged as a direct link) exposing two items: **Trends** (today's page, unchanged) and **Comparison** (new, `/financial/compare`) — comparing any two same-grain periods (Month vs Month, Quarter vs Quarter, or Year vs Year; mixed grains rejected as not like-for-like) for a user-picked **comparison node**, restricted to Reporting Root/Reporting Node types (Posting GL Accounts excluded — they're always leaf rows, and even ones with Driver/Driver Formula children can't feed an RM-denominated bridge since those children carry incomparable units like days/usd-per-day/ratio).

The page renders two views of the same diff: a **delta profit bridge** (one waterfall — start bar = Period A total, one bar per direct GL child showing its B−A delta colored favourable/adverse by polarity per ADR-0023's sign convention, end bar = Period B total — not two side-by-side static bridges) and a **table** (comparison node's full subtree, same recursive expand/collapse as today's statement table, but 3 columns — Period A / Period B / Delta — instead of 12 months). Driver/Driver Formula rows appear in the table only (never the bridge), with a neutral delta and no favourable/adverse coloring, since polarity doesn't apply to their units.

A new `GET /api/gl/comparison?scope=&periodA=&periodB=&node=` endpoint computes the diff server-side and returns only the subtree rooted at `node` (not the full ~1171-node tree), calling the existing `build_tree()`/`scoped_sum()` twice internally, untouched.

**Considered and rejected**: two parallel client-side `GET /api/gl/tree` calls (no backend change, frontend diffs) — rejected in favor of the new endpoint despite the larger backend surface, to keep the diff/polarity logic in one place server-side rather than duplicating it in the frontend.

**Status**: accepted
