# Theme activation: OS preference by default, manual toggle overrides and persists

Dark mode follows `prefers-color-scheme` by default (`frontend/src/styles/tokens/colors-dark.css`'s `@media` block). A toggle button in the navbar (`frontend/src/lib/theme.ts`) lets the user explicitly override it; the override is written to `localStorage` under `zeteo-theme` and applied via a `data-theme` attribute on `<html>`, which wins over the OS media query at the CSS specificity level. If no override is stored, the effective theme continues to track OS changes live (`watchSystemTheme`).

**Status**: accepted
