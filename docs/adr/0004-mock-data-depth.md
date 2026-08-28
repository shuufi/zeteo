# Mock data: one fully-modelled path, everything else shallow with a "not yet modelled" state

The wireframe's Driver Diagnostic mockups (1f/1g/1h) only ever detail one node — Expenses › Vessel Operating Cost › Repairs & Maintenance, Petroleum, FY26 Q3 — with exact trend/contribution/benchmark/root-cause figures. Rather than fabricating equivalent depth for every VDT node (high authoring cost, false impression of completeness) or wiring only that single hardcoded path (dead-end clicks everywhere else), every node in `frontend/src/lib/data/zeteo-data.ts` carries plausible top-line numbers (actual/budget/variance), but only `repairs-maintenance` carries `hasFullData: true` with trend, contribution drivers, sensitivity, benchmark and root-cause content. Every other node's Driver Diagnostic view renders `NotYetModelled` with a link to the fully-modelled example, so navigation never dead-ends and the scope boundary stays honest and visible.

**Status**: accepted
