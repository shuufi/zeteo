---
status: accepted
---

# Dark mode now sourced from app.sample.html's dark: classes, not derived

ADR 0009 derived dark-mode colors algorithmically because June had no dark tokens to source from. Now that colors come from `app.sample.html` (ADR 0011), that constraint is gone — the sample specifies its own dark values directly (`dark:bg-indigo-800` navbar, `dark:bg-gray-900`/`dark:bg-gray-800` surfaces). `colors-dark.css` was rewritten to use those values directly instead of an inversion formula. The trigger mechanism (OS preference by default, manual toggle override persisted to `localStorage`) is unchanged from ADR 0010.

**Supersedes**: `0009-dark-mode-derived-not-sourced.md`

**Status**: superseded by `0016-tailwind-css-migration.md` — `colors-dark.css` is deleted; dark mode is Tailwind's `dark:` variant driven by a `.dark` class, same OS-detect + manual-override trigger logic from ADR 0010.
