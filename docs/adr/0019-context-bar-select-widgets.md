# Context bar chips rebuilt on Tailwind Plus Elements `el-select`; Period/vs Budget gain a real picker, still no data effect

`0015` promoted the Business chip to a live BU/Company picker while leaving Period and vs Budget as static, unclickable spans per `0005`. This ADR does two things: (1) rebuilds `BusinessPicker` on `@tailwindplus/elements`' `el-select`/`el-option` web components instead of a hand-rolled `clickOutside`-driven dropdown, matching the Tailwind Plus select pattern already used for the nav menu (`el-dropdown`/`el-menu` in `NavBar.svelte`); (2) extracts a reusable `ChipSelect.svelte` on the same `el-select` primitive and uses it to turn Period and vs Budget into real, keyboard-navigable dropdowns with mock option lists (`FY26 Q1–Q4`; `vs Budget` / `vs Prior Year` / `vs Forecast`).

Selecting an option only updates the chip's own displayed label (via `el-select`'s built-in `el-selectedcontent` sync) — it still does not filter or recompute any P&L, VDT, or KPI data, since no mock node in `zeteo-data.ts` is scoped per-period or per-comparison today. The inert-data contract from `0005`/`0015` is unchanged; only the widget's interactivity and visual chrome changed.

**Status**: supersedes the "Period and vs Budget stay decorative [as static spans]" framing in `0015` — they are now interactive select widgets, still without data effect.
