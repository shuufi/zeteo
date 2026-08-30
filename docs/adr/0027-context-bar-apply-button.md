# Business/Period pickers stage a draft; a new Apply button in the Context Bar commits it

`0015` and `0026` made the Business and Period chips live pickers that refetch `GET /api/gl/tree` the instant an option is picked. That's fine for one chip at a time, but picking a new company *then* a new quarter fires two separate fetches back to back, and there's no way to change both before the page reacts — every intermediate pick is visible on every other screen for a moment. A new Apply button, next to the vs Budget/Forecast chip, changes this: picking a company or period now only updates a **draft** (`scopeDraft`/`periodDraft` — new modules alongside `scopeState`/`periodState`), which drives the picker's own displayed label but nothing else. `scopeState`/`periodState` — the values `gl-store.ts`, `VdtRanked`, `DriverDiagnostic`, and `FinancialPerformance` all actually read — only change when Apply is clicked, which commits both drafts at once and fires a single `loadScope`.

Each draft mirrors its applied counterpart reactively until the user picks something (a `dirty` flag), so it can never go stale against an applied change from elsewhere — e.g. Apply itself, or a Financial Performance P&L cell deep-link setting `?period=` directly. Deep-links and the Business picker's own initial-fallback default are unaffected by this ADR — they're not "the user changed a dropdown," so they still commit immediately, as before.

Rejected: making Apply commit only whichever one of the two pickers is dirty and leaving the other live — the whole point was one predictable moment where the page updates, not a per-chip special case.

**Status**: accepted
