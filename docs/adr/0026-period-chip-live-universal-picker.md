# Period chip becomes a live, universal Year/Quarter/Month picker — supersedes the month deep-link

`0005` and `0015` left Period decorative because no real dataset sat behind it. `0025` changes that — Period is now real hierarchical master data, and the only existing way to scope to a single month (clicking a Financial Performance P&L column, which deep-links into VDT Explorer via `?month=Jun`) is a one-off, VDT-Explorer-only mechanism with no equivalent for Year or Quarter. The Context Bar's Period chip becomes the one control for Year/Quarter/Month scope on VDT Explorer and Driver Diagnostic via a shared `?period=<code>` param; the P&L cell links become shortcuts that set the same param rather than a separate code path.

Financial Performance is the one exception, deliberately: it's a whole-P&L landing whose Income Statement table always shows all 12 months regardless of scope, and its KPI cards are explicitly labelled "YTD" — scoping them to an arbitrary quarter would make that label lie. So Financial Performance forces the chip back to the whole fiscal year the instant it detects a sub-year selection (a standing effect, not a one-time reset on mount, since the chip stays visible and interactive on this page too) rather than actually filtering its own data by it.

The chip's widget follows `BusinessPicker.svelte`'s precedent (an `Autocomplete.svelte`-based grouped dropdown, per `0015`/`0020`) rather than the flat `ChipSelect` it uses today, extended one level deeper: Year header → Quarter sub-header → Month leaf. Default selection on load is the Year (whole FY) — matching today's unfiltered full-year view, rather than the arbitrary quarter the old mock defaulted to.

Rejected: keeping the cell-link mechanism as a separate, additional entry point alongside the new chip — two ways to pick a period risks them disagreeing about what's currently selected. Also rejected: letting Financial Performance's KPIs/bridge genuinely scope to the chip's selection like the other two screens — it would contradict their own "YTD" labelling.

**Status**: accepted
