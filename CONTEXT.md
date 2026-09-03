# Zeteo Frontend

The diagnostic dashboard UI for Zeteo — the Value Driver Tree explorer, driver diagnostics, and the exception-driven CFO journey described in `docs/URS_Zeteo_v2.2.md`. This file captures IA/UI-specific language that crystallised while building `frontend/`; business and data-platform terms (VDT, Gold Layer, EDH, etc.) are already defined in the URS Terminology table and are not repeated here — only the concepts specific to this context.

## Language

**Accounting hierarchy**:
The GL/FSI reporting tree — Reporting Root (`NPAT`), Reporting Nodes (subtotal categories grouped by GL nature, e.g. Manpower Cost, Materials And Supplies, Repairs And Maintenance), Posting GL Accounts as leaves. Unchanged since ADR-0022; Trends is its home screen. See `docs/adr/0033-vdt-activity-hierarchy-alongside-accounting.md`.
_Avoid_: "VDT" or "VDT node" for this tree — that term now belongs to the VDT hierarchy below; this one is Accounting.

**VDT hierarchy**:
The activity-based tree — same Reporting Root and, outside the pilot scope, the same shared Reporting Nodes as the Accounting hierarchy, but within Cost of Revenue and Revenue its mid-tier is Activity Nodes (e.g. Crew Pay and Benefits Cost, Crew Traveling and Welfare Cost) instead of Reporting Nodes, terminating in its own Posting Activity Account leaves rather than reusing Posting GL Accounts. VDT Explorer is its home screen. See `docs/adr/0033-vdt-activity-hierarchy-alongside-accounting.md`.
_Avoid_: assuming VDT hierarchy totals reconcile to the Accounting hierarchy's totals within the pilot scope — they don't, by design (see Posting Activity Account); only outside the pilot scope, where nodes are literally shared, do they.

**Activity Node**:
The VDT hierarchy's non-leaf node type within Cost of Revenue/Revenue, replacing Reporting Node there — a named activity (not a GL-nature category) that Posting Activity Accounts roll up into. Coded `V` + 9 digits (branch digit + up to four 2-digit nesting-position segments, e.g. `V201000000`); the code is for human legibility only, `Parent Code` is the actual source of structure. See `docs/adr/0033-vdt-activity-hierarchy-alongside-accounting.md`.
_Avoid_: "VDT node" (retired, ambiguous between the two hierarchies — say Activity Node specifically).

**Posting Activity Account**:
The VDT hierarchy's terminal line within Cost of Revenue/Revenue — a named item (e.g. "Senior officer nationality mix") with its own Driver Formula computing its own RM amount, the same shape as a Driver Formula target (see below) rather than a `GLFact` row. Carries an `FA GL` pointer to the real Posting GL Account it's conceptually explaining — a display/reconciliation anchor, **not identity**: the pointer can be many-to-one (several Posting Activity Accounts anchoring to one GL account, e.g. `docs/vdt-hierarchy-crew-cost.csv`'s Senior/Junior/Ratings officer nationality mix all anchoring to `5100100100`), and its amount is an independent estimate **not required to sum** to the anchor's real total — the gap between them is the diagnostic signal the Reconciliation report surfaces, not an error to close. Coded separately from Activity Node, flat sequential `VA` + 8 digits (e.g. `VA00000001`), no positional encoding. See `docs/adr/0033-vdt-activity-hierarchy-alongside-accounting.md`.
_Avoid_: treating the `FA GL` pointer as a parent/allocation relationship (implies the amounts must reconcile — they don't); "VDT node" (retired).

**Reporting Node**:
The Accounting hierarchy's non-leaf subtotal node type (e.g. Manpower Cost, Repairs And Maintenance) — grouped by GL nature. Shared verbatim by the VDT hierarchy outside Cost of Revenue/Revenue.

**Posting GL Account**:
The Accounting hierarchy's leaf type — one real SAP GL code (e.g. `4010100100`), one `GLFact` value. Within Cost of Revenue/Revenue, the VDT hierarchy does not reuse these as its own leaves (see Posting Activity Account); outside that scope, both hierarchies share the same Reporting Node → Posting GL Account structure. May carry Driver/Driver Formula children (see below) — that decomposition is orthogonal to which hierarchy's tree the leaf sits in.

**Driver**:
A reusable named quantity (e.g. Crew Complement, Payroll Rate) valued per company × month × scenario, with no fixed tree position of its own — the same Driver can feed multiple Driver Formulas. A Driver is either terminal (a raw value) or itself computed by one or more Driver Formulas bound to it as their target, which is what lets driver decomposition recurse to any depth. A Driver with no Formula and not referenced as anyone's term (e.g. the legacy charter-rate/utilization drivers) carries an optional `displayed_under` pointer to the GL leaf it historically explained — a display-only anchor, not part of the compute graph. See `docs/adr/0030-driver-formula-computed-gl-values.md`.
_Avoid_: Operational Driver (retired `GLNode`-based concept this replaces).

**Driver Formula**:
A named expression, restricted to sum-of-products (ordered terms, each a chain of Drivers combined by `×` or `÷`, terms summed with an optional per-formula sign), that computes the value of exactly one target — a GL Posting Account leaf or another Driver. Multiple Formulas may drive the same target; the target's value is the sum of all of them, replacing any independently-fabricated fact row for that target. Formulas never contain raw numeric literals or nested/parenthesized sub-expressions — a constant is modelled as a flat-valued Driver. See `docs/adr/0030-driver-formula-computed-gl-values.md`.
_Avoid_: "formula" alone (say Driver Formula — this is a specific bound, sum-of-products expression, not a general spreadsheet formula); "calculation" (too generic).

**Target (of a Driver Formula)**:
The single GL Posting Account leaf or Driver whose value a Driver Formula computes. A target can have multiple Formulas bound to it (summed); a Driver can itself be a target for other Formulas, letting driver decomposition recurse.
_Avoid_: "output" (implies a UI artifact rather than the bound relationship it actually is).

**VDT Explorer**:
The screen family for browsing the **VDT hierarchy** (not Accounting), reached via the **Value Driver** nav item. Landing on root is a full income-statement layout (same shape as Trends, but walking the VDT hierarchy). Below root, two independent view modes reached by separate routes — Ranked (`/vdt/:id`, a summary card + a children table ranked by contribution) and Tree (`/vdt-tree/:id`, a horizontal decomposition diagram). Ranked/Tree are not tabs of one screen; each has its own click model (Ranked rows open Driver Diagnostic directly; Tree nodes re-centre the diagram). See `docs/adr/0033-vdt-activity-hierarchy-alongside-accounting.md`.
_Avoid_: VDT Explorer for the tree view alone — the term covers all three (root statement, Ranked, Tree). Also avoid conflating it with Financial below — they're separate nav branches over different hierarchies, not one screen family.

**Financial (nav item)**:
The top-level nav item (`docs/adr/0031-financial-comparison-page.md`) whose hover dropdown holds two screens — **Trends** and **Comparison** — each documented below. Clicking "Financial" itself (rather than a dropdown item) is a direct link to Trends.
_Avoid_: calling this "VDT Explorer's landing state" — that was the wireframe's framing, superseded once Financial got its own nav item and route, separate from Value Driver.

**Trends**:
The full-P&L overview screen at `/financial`, reached via the Financial nav item's dropdown (or by clicking "Financial" itself). Shows the whole **Accounting hierarchy** statement (Freight & Charter Revenue down to NPAT, actual/budget/prior-year, subtotals shaded) plus 4 KPI cards and two illustrative charts (Revenue/Cost of Revenue/OPEX bar chart, profit-bridge waterfall). Every row down to the Posting GL Account leaf is expandable in place, and leaves with Driver/Driver Formula children expand one level further to show those; everything below NPAT's direct children starts collapsed, so the statement opens minimal and the user drills down explicitly — see `docs/adr/0029-financial-trends-drills-to-leaf.md`. It is not a VDT Explorer view mode and does not share tree data with it once Cost of Revenue/Revenue diverge (see `docs/adr/0033-vdt-activity-hierarchy-alongside-accounting.md`) — it's a separate landing over the Accounting hierarchy specifically. Clicking a leaf row still routes into VDT Explorer (`/vdt/:id`) for that same GL code, since leaves are shared between both hierarchies. See `docs/adr/0013-financial-performance-landing.md`.
_Avoid_: "Financial Performance" (retired term — this screen is just "Trends" now, "Financial" is the nav item one level up); implying it shares tree data with VDT Explorer — since ADR-0033 they're two different hierarchies over the same leaves, not one shared tree.

**Comparison**:
The screen at `/financial/compare`, reached via the Financial nav item's dropdown, for comparing a single **comparison node**'s value between two same-grain periods (both Month, both Quarter, or both Year — never mixed). Renders a delta profit bridge (one waterfall from Period A's total to Period B's total, one bar per direct GL child showing its change, colored favourable/adverse by polarity) and a 3-column table (Period A / Period B / Delta) for the comparison node's full subtree. Backed by `GET /api/gl/comparison`, which diffs server-side and returns only the comparison node's subtree. See `docs/adr/0031-financial-comparison-page.md`.
_Avoid_: "diff view", "delta page" — the screen is "Comparison".

**Comparison node**:
The Accounting hierarchy node a Comparison screen is anchored to — the root of the subtree its bridge and table both render. Restricted to Reporting Root/Reporting Node types; a Posting GL Account can never be a comparison node, even one with Driver/Driver Formula children, since those children's units (days, usd-per-day, ratio, etc.) aren't RM-comparable and can't feed a bridge. See `docs/adr/0031-financial-comparison-page.md`.
_Avoid_: "anchor node", "root node" (ambiguous with a node's own `Reporting Root` type).

**Driver Diagnostic (workspace)**:
The tabbed screen (`/diagnostic/:id/:tab`) for one node — Diagnose / Benchmark / Root Cause & Mitigation tabs, sharing one breadcrumb and context. Hierarchy-agnostic: the `:id` is a GL code, Reporting Node, or Activity Node, whichever hierarchy the user drilled in from. Opened either from an exception, a VDT Explorer row, or a Home driver link.
_Avoid_: driver detail page, node detail.

**Context bar**:
The persistent strip pinned across every screen showing Business / Period / vs Budget filter chips, an Apply button, plus, where relevant, the breadcrumb back to the tree root. vs Budget remains decorative (see `docs/adr/0005-inert-filters-live-navigation.md`); the Business chip (`docs/adr/0015-business-chip-live-picker.md`, `docs/adr/0028-company-hierarchical-master-data.md`) and the Period chip (see Period below) are both live pickers, but picking an option only stages a draft — Apply is what actually commits it and refetches (see `docs/adr/0027-context-bar-apply-button.md`). The breadcrumb is live navigation, unaffected by Apply.

**Period**:
A node in a Year → Quarter → Month hierarchy (e.g. `FY26`, `FY26-Q3`, `FY26-M06`) that scopes actual/budget/prior-year figures on VDT Explorer and Driver Diagnostic via the Context Bar's Period chip, an accordion-style Year/Quarter/Month dropdown (deliberately not searchable like the Business chip — see `docs/adr/0026`). Three fiscal years — `FY24`, `FY25`, `FY26` — coexist as sibling Year roots, each with its own Quarter/Month children; Quarter/Month labels are year-qualified ("Jan FY24") since the bare month/quarter name repeats across years. "Prior year" always means the real prior Year's own actuals now, not a separately-stored scenario — see `docs/adr/0032-single-company-multi-year-focus.md`. Trends is the one screen the chip doesn't scope — the chip is still there and interactive, but that page's Income Statement always shows all 12 months of whichever year is current and its KPI cards are always labelled "YTD", regardless of the current pick. Comparison doesn't use the Period chip at all — it has its own two same-grain period pickers (Period A / Period B), independent of the Context Bar, which can span any two years. Only a Month is **postable** — the only grain a GL fact can be recorded against; Year and Quarter exist purely to roll postable Month figures up for reporting, the same relationship Reporting Nodes have to Posting GL Accounts in the Accounting hierarchy (and Activity Nodes have to Posting GL Accounts in the VDT hierarchy). See `docs/adr/0025-period-hierarchical-master-data.md`, `docs/adr/0026-period-chip-live-universal-picker.md`, and `docs/adr/0032-single-company-multi-year-focus.md`.
_Avoid_: "period" for an arbitrary date range — it always means one specific node in this hierarchy; "postable" for Year/Quarter nodes (only Month is postable); "the fiscal year" singular — there are three now.

**MISC Group**:
The root of the Business chip's hierarchy — MISC Group → Business Unit → Company, hierarchical master data (`company_node`, adjacency-list, mirrors Period's `Year → Quarter → Month` shape) rather than a curated JSON blob. Selecting it rolls up every Sampled company across all Business Units. See `docs/adr/0028-company-hierarchical-master-data.md`.

**Business Unit (BU)**:
MISC Group's grouping of legal entities — AET, Offshore Business Unit (OBU), MISC Maritime Services (MMS), Sungai Udang Port Sdn Bhd (SUPSB), ALAM. Each BU groups one or more **Company** records (a specific legal entity, e.g. "AET Tanker Holdings Sdn. Bhd."). This is distinct from the 7 "solution divisions" MISC's public website markets (Petroleum and Product Shipping, Gas Assets and Solutions, etc.) — that's a marketing/segment framing, not the BU grouping the company data actually uses. Zeteo models BU, not the marketing divisions.
_Avoid_: "business segment" for BU (that's the website's marketing term, not this data's grouping); "subsidiary" alone for Company (BU is also a kind of grouping, be specific about which level).

**Not-yet-modelled (state)**:
The empty-state shown when a node (in either hierarchy) lacks full diagnostic data (trend/contribution/benchmark/root-cause), or when a node has no fact data for the selected company/BU scope (see Sampled company). Distinguishes "this doesn't exist yet" from a routing error. Always carries a link to the one fully-modelled example node, `PNL-0024` (Repairs And Maintenance, Cost of Revenue). See `docs/adr/0004-mock-data-depth.md` and `docs/adr/0024-gl-fact-data-company-sampling.md`.
_Avoid_: empty state (too generic — this is a specific, deliberate placeholder for unmodelled tree depth or unsampled scope, not an empty list/search result).

**Sampled company**:
The single company — `0190`, MISC Ship Management Sdn. Bhd. — that carries fabricated GL fact data, across three fiscal years (see Period). Selecting any other company, or a BU/Group with no sampled company under it, renders Not-yet-modelled rather than fabricated figures. Previously 9 companies (3 per Business Unit); narrowed to one for a coherent, designed dataset rather than noise spread thin — see `docs/adr/0024-gl-fact-data-company-sampling.md` and `docs/adr/0032-single-company-multi-year-focus.md`.
_Avoid_: modelled company (overloads "modelled," already used for diagnostic depth in Not-yet-modelled).

**Partial BU total**:
The figure shown when a Business Unit or MISC Group (not a specific company) is selected — the sum of only that scope's Sampled companies, visibly labelled with the count (e.g. "3 of 57 companies", or "9 of 86 companies" for the whole Group) rather than presented as the scope's true total.
_Avoid_: BU total / Group total alone (implies a completeness the figure doesn't have).

**Attention item (exception)**:
The single highlighted card on Home surfacing the largest adverse variance needing investigation. Distinct from a "top adverse driver" (a plain ranked list row) — an attention item is the one thing Home foregrounds for immediate action.

**Leading indicator / lagging indicator**:
Leading indicators (e.g. maintenance backlog, off-hire days) signal what's coming; lagging indicators (the KPI row, variance tables) confirm what already happened. Rendered with a distinct visual treatment (dashed blue) and never mixed into the same list as lagging KPIs.

**FACT / AI HYPOTHESIS (root-cause entry)**:
The two states of a root-cause entry. FACT entries carry cited evidence and are shown with solid black styling. AI HYPOTHESIS entries carry an AI confidence level and rationale, are shown with dashed-blue styling, and remain AI-proposed until a human sets their status to Validated or Rejected — only a human can make that transition.
_Avoid_: finding, cause (ambiguous about provenance — always say which type).
