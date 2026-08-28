# Reuse the June Design System's exported CSS tokens verbatim as Zeteo's visual system

`docs/design.md` documents "June," a B2B SaaS analytics brand unrelated to Zeteo/MISC, with a synced Design System project exporting real token CSS (`colors.css`, `spacing.css`, `radius.css`, `typography.css`) and a component bundle. Rather than hand-rolling fresh tokens from the design.md prose or leaving the prototype in its original hand-drawn wireframe sketch style, we copied the exported token files into `frontend/src/styles/tokens/` unmodified and layered one small Zeteo-specific extension file (`tokens/zeteo.css`) on top for semantics June has no equivalent for (adverse/favourable variance color, the AI-hypothesis/leading-indicator accent blue). The vendored June files are not edited in place, so they stay a clean diff-able mirror of the source project.

Rejected: hand-rolling tokens from design.md's prose (risks transcription drift from the real hex/px values); designing a bespoke MISC/maritime brand now (explicitly deferred — see `CONTEXT.md`, this may be revisited before production).

**Status**: superseded by `0016-tailwind-css-migration.md` — the vendored June token files and Nunito/Inter fonts are deleted; the app runs on Tailwind CSS v4's own default theme.
