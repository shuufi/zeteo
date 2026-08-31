# Zeteo Frontend

The diagnostic dashboard UI for Zeteo — the Value Driver Tree explorer, driver diagnostics, and the exception-driven CFO journey described in `docs/URS_Zeteo_v2.2.md`. This file captures IA/UI-specific language that crystallised while building `frontend/`; business and data-platform terms (VDT, Gold Layer, EDH, etc.) are already defined in the URS Terminology table and are not repeated here — only the concepts specific to this context.

## Language

**VDT node**:
A single addressable point in the Value Driver Tree — a GL/FSI hierarchy position (reporting root, reporting/subtotal node, posting GL account) or an operational driver — carrying its own actual/budget/variance and, optionally, trend, contribution drivers, benchmark and root-cause data. Identified by a stable `nodeId`, the real SAP GL/FSI code (e.g. `PNL-0024`, `4010100100`) rather than a curated slug. See `docs/adr/0022-gl-fsi-hierarchy-replaces-mock-vdt-tree.md`.
_Avoid_: item, row, entry (too generic — use "node" whenever it's a VDT tree position); GL account alone for a VDT node (a node can also be a reporting/subtotal node or operational driver, not just a posting account).

**VDT Explorer**:
The screen family for browsing the tree, reached via the **Value Driver** nav item. Has two independent view modes reached by separate routes — Ranked (`/vdt/:id`, a summary card + a children table ranked by contribution) and Tree (`/vdt-tree/:id`, a horizontal decomposition diagram). They are not tabs of one screen; each has its own click model (Ranked rows open Driver Diagnostic directly; Tree nodes re-centre the diagram).
_Avoid_: VDT Explorer for the tree view alone — the term covers both view modes. Also avoid conflating it with Financial Performance below — they're separate nav branches, not one screen family.

**Financial Performance (landing)**:
The full-P&L overview screen at `/financial`, reached via its own top-level nav item. Shows the whole statement (Freight & Charter Revenue down to NPAT, actual/budget/prior-year, subtotals shaded) plus 4 KPI cards and two illustrative charts (Revenue/Cost of Revenue/OPEX bar chart, profit-bridge waterfall), all computed live from the same VDT node data VDT Explorer uses. Every row down to the Posting GL Account leaf is expandable in place, and the handful of leaves with Operational Driver children (see VDT node) expand one level further to show those; everything below NPAT's direct children starts collapsed, so the statement opens minimal and the user drills down explicitly — see `docs/adr/0029-financial-trends-drills-to-leaf.md`. It is not a VDT Explorer view mode — it's a separate landing a user lands on before drilling into any one line; clicking a line routes into VDT Explorer (`/vdt/:id`) for that node. See `docs/adr/0013-financial-performance-landing.md`.
_Avoid_: calling this "VDT Explorer's landing state" — that was the wireframe's framing, superseded once Financial Performance got its own nav item and route, separate from Value Driver.

**Driver Diagnostic (workspace)**:
The tabbed screen (`/diagnostic/:id/:tab`) for one VDT node — Diagnose / Benchmark / Root Cause & Mitigation tabs, sharing one breadcrumb and context. Opened either from an exception, a VDT Explorer row, or a Home driver link.
_Avoid_: driver detail page, node detail.

**Context bar**:
The persistent strip pinned across every screen showing Business / Period / vs Budget filter chips, an Apply button, plus, where relevant, the breadcrumb back to the tree root. vs Budget remains decorative (see `docs/adr/0005-inert-filters-live-navigation.md`); the Business chip (`docs/adr/0015-business-chip-live-picker.md`, `docs/adr/0028-company-hierarchical-master-data.md`) and the Period chip (see Period below) are both live pickers, but picking an option only stages a draft — Apply is what actually commits it and refetches (see `docs/adr/0027-context-bar-apply-button.md`). The breadcrumb is live navigation, unaffected by Apply.

**Period**:
A node in the Year → Quarter → Month hierarchy (e.g. `FY26`, `FY26-Q3`, `FY26-M06`) that scopes actual/budget/prior-year figures on VDT Explorer and Driver Diagnostic via the Context Bar's Period chip, an accordion-style Year/Quarter/Month dropdown (deliberately not searchable like the Business chip — see `docs/adr/0026`). Financial Performance is the one screen the chip doesn't scope — the chip is still there and interactive, but that page's Income Statement always shows all 12 months and its KPI cards are always labelled "YTD", regardless of the current pick. Only a Month is **postable** — the only grain a GL fact can be recorded against; Year and Quarter exist purely to roll postable Month figures up for reporting, the same relationship Reporting Nodes have to Posting GL Accounts in the VDT node hierarchy. See `docs/adr/0025-period-hierarchical-master-data.md` and `docs/adr/0026-period-chip-live-universal-picker.md`.
_Avoid_: "period" for an arbitrary date range — it always means one specific node in this hierarchy; "postable" for Year/Quarter nodes (only Month is postable).

**MISC Group**:
The root of the Business chip's hierarchy — MISC Group → Business Unit → Company, hierarchical master data (`company_node`, adjacency-list, mirrors Period's `Year → Quarter → Month` shape) rather than a curated JSON blob. Selecting it rolls up every Sampled company across all Business Units. See `docs/adr/0028-company-hierarchical-master-data.md`.

**Business Unit (BU)**:
MISC Group's grouping of legal entities — AET, Offshore Business Unit (OBU), MISC Maritime Services (MMS), Sungai Udang Port Sdn Bhd (SUPSB), ALAM. Each BU groups one or more **Company** records (a specific legal entity, e.g. "AET Tanker Holdings Sdn. Bhd."). This is distinct from the 7 "solution divisions" MISC's public website markets (Petroleum and Product Shipping, Gas Assets and Solutions, etc.) — that's a marketing/segment framing, not the BU grouping the company data actually uses. Zeteo models BU, not the marketing divisions.
_Avoid_: "business segment" for BU (that's the website's marketing term, not this data's grouping); "subsidiary" alone for Company (BU is also a kind of grouping, be specific about which level).

**Not-yet-modelled (state)**:
The empty-state shown when a VDT node lacks full diagnostic data (trend/contribution/benchmark/root-cause), or when a node has no fact data for the selected company/BU scope (see Sampled company). Distinguishes "this doesn't exist yet" from a routing error. Always carries a link to the one fully-modelled example node, `PNL-0024` (Repairs And Maintenance, Cost of Revenue). See `docs/adr/0004-mock-data-depth.md` and `docs/adr/0024-gl-fact-data-company-sampling.md`.
_Avoid_: empty state (too generic — this is a specific, deliberate placeholder for unmodelled tree depth or unsampled scope, not an empty list/search result).

**Sampled company**:
One of the 9 companies (3 per Business Unit, or all of a BU's companies where it has 3 or fewer) that carries real fake GL fact data. Selecting any other company renders Not-yet-modelled rather than fabricated figures. See `docs/adr/0024-gl-fact-data-company-sampling.md`.
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
