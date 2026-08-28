# Pinned indigo scale re-anchored on MISC's brand blue

`0011`/`0016` pinned the `indigo` scale in `global.css`'s `@theme` block to Tailwind's own sRGB indigo hex values as a generic accent color. This re-anchors that same scale on `#00009d` — MISC's actual brand blue, sourced from the splash-screen logo fill on `miscgroup.com` (no published brand-color page was reachable; `brand.miscgroup.com` renders client-side and returned no usable markup). The rest of the ramp (100–950) keeps the brand's hue/saturation (H240°, S100%) and varies only lightness, with `#00009d` anchoring `indigo-600` — the shade used for buttons, links, and focus rings throughout the app.

Because the accent color is centralized in one `@theme` override rather than hardcoded per component, this is a single-file, zero-component-diff change — every `indigo-*` utility class across the app picks up the new value automatically.

**Status**: accepted
