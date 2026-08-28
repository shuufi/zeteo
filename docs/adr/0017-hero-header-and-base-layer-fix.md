# PageHeader adopts app.sample.html's colored hero band; global link-color rule moved into @layer base

Two related light-theme bugs were reported together: nav links were unreadable (indigo-600 text on indigo-600 background), and the title bar and filter chips read as too narrow compared to `app.sample.html`.

The nav link color bug was not a `NavBar.svelte` problem. `global.css` had `a { @apply text-indigo-600 dark:text-indigo-400; }` outside any `@layer` block. Under Tailwind v4's CSS cascade layers, unlayered CSS beats every layered utility class regardless of specificity, so this rule silently overrode `text-white` on every nav link in both themes — light mode just happened to make it invisible (identical color to the nav background) where dark mode's lighter indigo-400 stayed borderline legible. Fixed by wrapping the rule in `@layer base`, matching Tailwind's documented pattern for base-layer defaults that component utility classes are meant to override.

`PageHeader.svelte` — the "title bar" — was a plain `bg-white`/`border-b`, `py-5`, `text-2xl` bar, unrelated in style to `app.sample.html`'s colored `py-10`/`text-3xl` hero band (`0007` borrowed the sample's *layout* skeleton, not this styling; `0016`'s Tailwind migration didn't revisit it either). It now matches the sample: `bg-indigo-600 dark:bg-indigo-800` (same fill as `NavBar`, so nav and title bar read as one continuous band), `py-10`, `text-3xl font-bold text-white`, no border.

`ChipRow.svelte`'s chip pills went from `px-2.5 py-px text-xs` (~1px vertical padding, effectively flat) to `px-3 py-1.5 text-sm`, with the row's label span (e.g. "Segment by:", "Compare:") bumped to the same `text-sm` so the row stays visually uniform rather than pairing a now-larger chip against a smaller caption.

**Status**: superseded by `0018-full-hero-overlap-skeleton.md` — the initial cut kept `ContextBar` below the band on the normal page background with no overlap; a follow-up request to fully adopt the sample's skeleton reversed that and added the `-mt-32` card overlap across every route.
