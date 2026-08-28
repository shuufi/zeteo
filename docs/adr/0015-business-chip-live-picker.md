# Business chip becomes a live BU/Company picker; Period and vs Budget stay decorative

`0005` established that every context-bar chip is a dead click by design. The Business chip is promoted to a working accordion-tree dropdown (BU → Company, sourced from `0014`'s endpoint) because a real, addressable MISC company list exists and users expect to browse it — unlike Period/Comparison, which have no equivalent real dataset behind them yet. The picker only updates the chip's own label; it does not filter P&L, VDT, or KPI data, since no mock node in `zeteo-data.ts` is scoped per-company today. That remains genuinely decorative, same as `0005` intended — only the chip's interactivity changed, not its effect on the rest of the app.

**Status**: accepted
