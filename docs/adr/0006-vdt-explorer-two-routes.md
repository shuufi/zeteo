# VDT Explorer: ranked view and tree view are separate routes, not one screen with a toggle

The wireframe options 1c (ranked driver panel, marked "recommended") and 1d (horizontal decomposition tree) were two competing designs for the same idea. Rather than picking one or merging them into a single screen with a view-mode toggle, both were built as independent routes — `/vdt/:id` (ranked) and `/vdt-tree/:id` (tree) — cross-linked via a "View as ranked list / decomposition tree" link, each keeping its own click model (ranked rows open Driver Diagnostic directly; tree nodes re-centre the diagram). This was an explicit user decision during scoping, not a default.

**Status**: accepted
