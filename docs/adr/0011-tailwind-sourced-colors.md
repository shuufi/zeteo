---
status: accepted
---

# Colors sourced from app.sample.html's Tailwind indigo/gray, not June

The June-violet visual system (ADR 0003) read flat against the app-shell structure borrowed from `app.sample.html` — user feedback was that the result "looks ugly." Rather than keep chasing June's palette, `colors.css` and `colors-dark.css` were re-themed with the actual Tailwind indigo/gray hex values `app.sample.html` uses (indigo-600 `#4f46e5` primary, gray-900/500/200 for ink/mute/hairline, indigo-800/gray-900/800 for dark mode). Everything else — the CSS-custom-property architecture, spacing/radius/typography tokens, component structure — is untouched; this is a color-value swap, not a framework change (Tailwind CSS itself was explicitly not adopted, see ADR 0001/0007).

Two new roles were added because the sample uses a distinctly *different* indigo step for the navbar's own background fill than for accents elsewhere (`--nav-bg`/`--nav-bg-active`/`--nav-bg-hover`/`--nav-text`/`--nav-text-mute`, separate from `--primary`/`--accent`/`--link`). Collapsing them into one token would have made dark-mode badges and borders illegible once the navbar band needed a muted dark-indigo fill.

Semantic colors the sample doesn't define (success/error/warning, and Zeteo's own adverse/favourable/AI-hypothesis tokens in `zeteo.css`) were picked from the same Tailwind palette family (green-600, red-600, amber-500, blue-600) rather than sourced, since neither June nor the sample specify them.

**Supersedes**: `0003-june-tokens-as-visual-system.md`

**Status**: superseded by `0016-tailwind-css-migration.md` — `colors.css`/`colors-dark.css` are deleted; colors come from Tailwind's own default palette used directly as utility classes.
