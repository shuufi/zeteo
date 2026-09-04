# VDT Statement's Cost Bridge gains live period comparison (vs This Year / vs Last Year) plus an LLM-generated movement narration

Today VDT Statement's ("`/vdt`" landing) Cost Bridge is a single-period decomposition — SOC Crew Cost (`V201000000`) split into its direct children's actual values, no comparison axis. The Context Bar's `vs Budget` / `vs Prior Year` / `vs This Year` chip that sits above it is purely decorative (ADR-0005) everywhere it renders. This ADR activates that chip for VDT Statement specifically, reshapes the bridge into a genuine period-over-period comparison, and adds an LLM-generated narration explaining the movement — the first LLM integration in the codebase.

## Comparison modes

The chip's three options are relabelled `vs Budget` / `vs Last Year` / `vs This Year` (`vs Prior Year` renamed to match the language used to design this feature — same underlying "prior fiscal year" concept). Only `vs Last Year` and `vs This Year` gain live behavior; `vs Budget` stays inert on VDT Statement (no budget-comparison bridge shape defined yet).

- **vs This Year**: two Period pickers, Period A and Period B, both restricted to the current fiscal year (`FY26`) — arbitrary cross-year comparison already exists as the separate Comparison screen (ADR-0031); this mode is deliberately within-year. Defaults to the two most recent months, e.g. `FY26-08` and `FY26-09`.
- **vs Last Year**: one Period picker (defaults to the current month, `FY26-09`), the same month one fiscal year back is derived automatically (`FY25-09`) — mirrors how Trends' Period chip already treats "prior year" (ADR-0032): the real prior year's actuals, not a stored scenario.

Grain is fixed to Month for both modes — no Quarter/Year toggle, and "grain" is never surfaced as UI language; pickers are labelled "Period A"/"Period B" (or a single "Period" in `vs Last Year` mode). The YTD checkbox stays orthogonal to comparison mode: when on, it converts whichever period(s) are selected from single-month to Jan-through-that-month cumulative ranges, in both modes.

This activation is scoped to VDT Statement only. The same chip renders inert as before on Home, VDT Ranked, and Reconciliation; giving it live behavior there is a separate decision, not part of this change.

## Cost Bridge reshaped

The bridge changes from a same-period decomposition into a waterfall matching Comparison's existing shape (ADR-0031): start bar = SOC Crew Cost's total at Period A, one bar per direct child showing its Period A→B delta (colored increase/decrease), end bar = SOC Crew Cost's total at Period B. Backed by a new endpoint, `GET /api/vdt/comparison`, the VDT-hierarchy analogue of `GET /api/gl/comparison` — same request/response shape, different tree. The statement table below the bridge becomes comparison-aware too: Period A / Period B / Delta / Delta% columns for the same subtree, in place of today's single-period actual column.

## Movement narration

A new panel to the right of the bridge, populated on demand (an "Explain movement" button — never auto-fired on picker changes, to avoid an LLM call per keystroke/tweak) with an LLM-written explanation of what drove the change.

**Prompt payload is the full nested hierarchy, not a flat delta list** — root (SOC Crew Cost) → Activity Node children → Posting Activity Account leaves →, for formula-driven leaves, the Driver Formula's `expression_text` (ADR-0030) plus each Driver term's own Period A/B/delta values. This lets the narration attribute movement below the dollar level — e.g. "Crew Complement rose, Payroll Rate held flat" — rather than only naming which child moved. The full tree is sent unpruned; the VDT hierarchy's pilot scope (Cost of Revenue only, ADR-0033) is shallow enough that no top-N pruning is needed yet. All numbers in the prompt are backend-computed; the LLM is instructed to narrate only from the given facts, not to compute its own deltas or percentages, to keep arithmetic hallucination-free.

Output shape: one headline sentence summarizing net movement, followed by 2-4 bullets each naming a contributor and its driver-level cause where available.

**Architecture**: backend-mediated, a new `POST /api/vdt/narration` endpoint — the API key never reaches the browser, and the backend already owns the tree/formula data the prompt is built from. Model is `gpt-4o-mini` via a new `OPENAI_API_KEY` env var (none existed in this codebase before) and `OPENAI_MODEL` (defaults to `gpt-4o-mini`) — this is a "summarize given facts" task, not one that needs a larger model for a POC. Results are cached in-memory on the backend keyed by `(root, periodA, periodB, ytd)`, cleared on process restart; no persistence layer and no explicit regenerate action for now.

Narration failure (missing key, API error, timeout) is isolated to its own panel — an inline "unable to generate narration" message — and never blocks or degrades the bridge, table, or chart, which must keep working with or without OpenAI configured.

## Considered and rejected

**Auto-generating narration on every period change**: rejected — fires an OpenAI call on transient in-progress picker states, adds latency to what should be a fast comparison-browsing loop, and costs money per tweak rather than per deliberate "explain this" request.

**Sending only a flat top-N delta list to the LLM** (no hierarchy, no driver terms): rejected once it was clear the backend already computes real Driver/Driver Formula decomposition (ADR-0030) per period — a flat list would have discarded exactly the quantity-vs-rate attribution this feature is meant to surface.

**Activating the chip everywhere it renders** (Home, VDT Ranked, Reconciliation), not just VDT Statement: rejected as out of scope — those screens have no defined comparison behavior yet, and ADR-0005 made the chip inert deliberately; extending live behavior to them is a future, separate decision.

## Open items

`vs Budget` remains inert on VDT Statement — no budget-comparison bridge or narration shape is defined. Activating the chip on Home/VDT Ranked/Reconciliation is explicitly deferred. Narration has no explicit regenerate action; if results ever need to be refreshed within a process lifetime (e.g. underlying facts change), that's future work.

**Status**: accepted
