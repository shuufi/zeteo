# Dark mode: palette derived by systematic inversion, not sourced from June

The sample shell supports dark mode throughout, but the June Design System project has no dark tokens — its own readme confirms dark mode wasn't addressed in the source brief. Rather than borrowing Tailwind's indigo/gray dark values from the sample (a different color language than June) or leaving dark mode unstyled, `frontend/src/styles/tokens/colors-dark.css` derives every dark value algorithmically from June's light tokens: canvas/ink invert, the violet accent brightens for AA contrast on dark backgrounds, hairlines lighten via near-black tints. This is a design decision made without source-of-truth confirmation from the June project and should be revisited if real dark-mode tokens ever get added there.

**Status**: superseded by `0012-dark-mode-sourced-not-derived.md`
