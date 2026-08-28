# Zeteo Frontend

The diagnostic dashboard UI for Zeteo — the Value Driver Tree explorer, driver diagnostics, and the exception-driven CFO journey described in `docs/URS_Zeteo_v2.2.md`. This file captures IA/UI-specific language that crystallised while building `frontend/`; business and data-platform terms (VDT, Gold Layer, EDH, etc.) are already defined in the URS Terminology table and are not repeated here — only the concepts specific to this context.

## Language

**VDT node**:
A single addressable point in the Value Driver Tree — a financial metric or an operational driver — carrying its own actual/budget/variance and, optionally, trend, contribution drivers, benchmark and root-cause data. Identified by a stable `nodeId` (e.g. `vessel-operating-cost`) used in every route.
_Avoid_: item, row, entry (too generic — use "node" whenever it's a VDT tree position).

**VDT Explorer**:
The screen family for browsing the tree, reached via the **Value Driver** nav item. Has two independent view modes reached by separate routes — Ranked (`/vdt/:id`, a summary card + a children table ranked by contribution) and Tree (`/vdt-tree/:id`, a horizontal decomposition diagram). They are not tabs of one screen; each has its own click model (Ranked rows open Driver Diagnostic directly; Tree nodes re-centre the diagram).
_Avoid_: VDT Explorer for the tree view alone — the term covers both view modes. Also avoid conflating it with Financial Performance below — they're separate nav branches, not one screen family.

**Financial Performance (landing)**:
The full-P&L overview screen at `/financial`, reached via its own top-level nav item. Shows the whole statement (Freight & Charter Revenue down to NPAT, actual/budget/prior-year, subtotals shaded) plus 4 KPI cards and two illustrative charts (Revenue/Cost of Revenue/OPEX bar chart, profit-bridge waterfall), all computed live from the same VDT node data VDT Explorer uses. It is not a VDT Explorer view mode — it's a separate landing a user lands on before drilling into any one line; clicking a line routes into VDT Explorer (`/vdt/:id`) for that node. See `docs/adr/0013-financial-performance-landing.md`.
_Avoid_: calling this "VDT Explorer's landing state" — that was the wireframe's framing, superseded once Financial Performance got its own nav item and route, separate from Value Driver.

**Driver Diagnostic (workspace)**:
The tabbed screen (`/diagnostic/:id/:tab`) for one VDT node — Diagnose / Benchmark / Root Cause & Mitigation tabs, sharing one breadcrumb and context. Opened either from an exception, a VDT Explorer row, or a Home driver link.
_Avoid_: driver detail page, node detail.

**Context bar**:
The persistent strip pinned across every screen showing Business / Period / vs Budget filter chips plus, where relevant, the breadcrumb back to the tree root. Period and vs Budget remain decorative (see `docs/adr/0005-inert-filters-live-navigation.md`); the Business chip is a live picker (see `docs/adr/0015-business-chip-live-picker.md`) and the breadcrumb is live navigation.

**Business Unit (BU)**:
MISC's internal top-level grouping of legal entities — AET, Offshore Business Unit (OBU), MISC Maritime Services (MMS), Sungai Udang Port Sdn Bhd (SUPSB), ALAM. Each BU groups one or more **Company** records (a specific legal entity, e.g. "AET Tanker Holdings Sdn. Bhd."). This is distinct from the 7 "solution divisions" MISC's public website markets (Petroleum and Product Shipping, Gas Assets and Solutions, etc.) — that's a marketing/segment framing, not the BU grouping the company data actually uses. Zeteo models BU, not the marketing divisions.
_Avoid_: "business segment" for BU (that's the website's marketing term, not this data's grouping); "subsidiary" alone for Company (BU is also a kind of grouping, be specific about which level).

**Not-yet-modelled (state)**:
The empty-state shown when a VDT node lacks full diagnostic data (trend/contribution/benchmark/root-cause). Distinguishes "this node exists but hasn't been modelled yet" from a routing error. Always carries a link to the one fully-modelled example node, `repairs-maintenance`. See `docs/adr/0004-mock-data-depth.md`.
_Avoid_: empty state (too generic — this is a specific, deliberate placeholder for unmodelled tree depth, not an empty list/search result).

**Attention item (exception)**:
The single highlighted card on Home surfacing the largest adverse variance needing investigation. Distinct from a "top adverse driver" (a plain ranked list row) — an attention item is the one thing Home foregrounds for immediate action.

**Leading indicator / lagging indicator**:
Leading indicators (e.g. maintenance backlog, off-hire days) signal what's coming; lagging indicators (the KPI row, variance tables) confirm what already happened. Rendered with a distinct visual treatment (dashed blue) and never mixed into the same list as lagging KPIs.

**FACT / AI HYPOTHESIS (root-cause entry)**:
The two states of a root-cause entry. FACT entries carry cited evidence and are shown with solid black styling. AI HYPOTHESIS entries carry an AI confidence level and rationale, are shown with dashed-blue styling, and remain AI-proposed until a human sets their status to Validated or Rejected — only a human can make that transition.
_Avoid_: finding, cause (ambiguous about provenance — always say which type).
